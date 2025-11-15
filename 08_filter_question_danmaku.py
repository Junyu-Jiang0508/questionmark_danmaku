import json
import os
import pandas as pd
import glob
from typing import List, Dict

def load_matched_data(matched_file: str) -> pd.DataFrame:
    """
    加载已匹配的弹幕字幕数据
    """
    return pd.read_csv(matched_file)

def get_subtitles_in_window(bvid: str, center_time: float, window_seconds: float = 15, 
                            subtitle_dir: str = "Data") -> List[Dict]:
    """
    获取指定时间前后window_seconds秒内的所有字幕
    """
    json_path = os.path.join(subtitle_dir, f"{bvid}_subtitle.json")
    if not os.path.exists(json_path):
        return []
    
    with open(json_path, 'r', encoding='utf-8') as f:
        subtitles = json.load(f)
    
    start_time = center_time - window_seconds
    end_time = center_time + window_seconds
    
    result = []
    for sub in subtitles:
        if (sub['from'] >= start_time and sub['from'] <= end_time) or \
           (sub['to'] >= start_time and sub['to'] <= end_time) or \
           (sub['from'] <= start_time and sub['to'] >= end_time):
            result.append({
                'from': sub['from'],
                'to': sub['to'],
                'content': sub['content'],
                'time_diff': sub['from'] - center_time
            })
    
    return result

def get_danmaku_in_window(df: pd.DataFrame, center_time: float, window_seconds: float = 15) -> pd.DataFrame:
    """
    获取指定时间前后window_seconds秒内的所有弹幕
    """
    start_time = center_time - window_seconds
    end_time = center_time + window_seconds
    
    window_df = df[(df['danmaku_time'] >= start_time) & (df['danmaku_time'] <= end_time)].copy()
    window_df['time_diff'] = window_df['danmaku_time'] - center_time
    
    return window_df

def filter_question_danmaku(matched_dir: str = "matched_results", 
                           output_dir: str = "question_analysis",
                           window_seconds: float = 15):
    """
    筛选包含"？"的弹幕及其周围的弹幕和字幕
    """
    os.makedirs(output_dir, exist_ok=True)
    
    matched_files = glob.glob(os.path.join(matched_dir, "*_matched.csv"))
    
    all_results = []
    
    for matched_file in matched_files:
        filename = os.path.basename(matched_file)
        bvid = filename.replace("_matched.csv", "")
        
        try:
            df = load_matched_data(matched_file)
            
            if len(df) == 0 or 'danmaku_content' not in df.columns:
                continue
            
            question_danmaku = df[df['danmaku_content'].astype(str).str.contains('？', na=False)]
            
            if len(question_danmaku) == 0:
                continue
            
            for idx, question_row in question_danmaku.iterrows():
                center_time = question_row['danmaku_time']
                
                nearby_danmaku = get_danmaku_in_window(df, center_time, window_seconds)
                nearby_subtitles = get_subtitles_in_window(bvid, center_time, window_seconds)
                
                result = {
                    'bvid': bvid,
                    'question_danmaku': question_row['danmaku_content'],
                    'question_time': center_time,
                    'question_subtitle': question_row['subtitle_content'],
                    'nearby_danmaku_count': len(nearby_danmaku),
                    'nearby_subtitle_count': len(nearby_subtitles),
                    'nearby_danmaku': nearby_danmaku.to_dict('records'),
                    'nearby_subtitles': nearby_subtitles
                }
                
                all_results.append(result)
        
        except Exception as e:
            print(f"[ERROR] {bvid}: {str(e)}")
            continue
    
    with open(os.path.join(output_dir, "question_danmaku_analysis.json"), 'w', encoding='utf-8') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    summary_data = []
    for result in all_results:
        summary_data.append({
            'bvid': result['bvid'],
            'question_danmaku': result['question_danmaku'],
            'question_time': result['question_time'],
            'question_subtitle': result['question_subtitle'],
            'nearby_danmaku_count': result['nearby_danmaku_count'],
            'nearby_subtitle_count': result['nearby_subtitle_count']
        })
    
    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(os.path.join(output_dir, "question_danmaku_summary.csv"), 
                     index=False, encoding='utf-8-sig')
    
    print(f"筛选完成: 共找到 {len(all_results)} 条包含问号的弹幕")
    print(f"结果已保存到 {output_dir} 目录")
    
    return all_results, summary_df

def export_detailed_context(results: List[Dict], output_dir: str = "question_analysis"):
    """
    导出每个问号弹幕的详细上下文到单独的文本文件
    """
    context_dir = os.path.join(output_dir, "detailed_contexts")
    os.makedirs(context_dir, exist_ok=True)
    
    for i, result in enumerate(results):
        output_file = os.path.join(context_dir, f"{result['bvid']}_{i+1}.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"视频: {result['bvid']}\n")
            f.write(f"问号弹幕: {result['question_danmaku']}\n")
            f.write(f"时间: {result['question_time']:.2f}秒\n")
            f.write(f"对应字幕: {result['question_subtitle']}\n")
            f.write(f"\n{'='*60}\n")
            
            f.write(f"\n前后15秒的字幕内容:\n")
            f.write(f"{'-'*60}\n")
            sorted_subtitles = sorted(result['nearby_subtitles'], key=lambda x: x['from'])
            for sub in sorted_subtitles:
                time_str = f"[{sub['from']:.1f}s - {sub['to']:.1f}s]"
                f.write(f"{time_str} {sub['content']}\n")
            
            f.write(f"\n{'='*60}\n")
            f.write(f"\n前后15秒的弹幕内容 (共{result['nearby_danmaku_count']}条):\n")
            f.write(f"{'-'*60}\n")
            sorted_danmaku = sorted(result['nearby_danmaku'], key=lambda x: x['danmaku_time'])
            for dm in sorted_danmaku:
                time_str = f"[{dm['danmaku_time']:.1f}s]"
                is_question = " [问号弹幕]" if '？' in str(dm['danmaku_content']) else ""
                f.write(f"{time_str} {dm['danmaku_content']}{is_question}\n")

if __name__ == "__main__":
    results, summary_df = filter_question_danmaku(
        matched_dir="matched_results",
        output_dir="question_analysis",
        window_seconds=10
    )
    
    if len(results) > 0:
        export_detailed_context(results, output_dir="question_analysis")
        print(f"\n详细上下文已导出到 question_analysis/detailed_contexts/ 目录")
        
        print(f"\n统计信息:")
        print(f"平均每个问号弹幕周围有 {summary_df['nearby_danmaku_count'].mean():.1f} 条弹幕")
        print(f"平均每个问号弹幕周围有 {summary_df['nearby_subtitle_count'].mean():.1f} 条字幕")

