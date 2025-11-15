import json
import os
import pandas as pd
import glob
from typing import List, Dict, Optional

def load_subtitle(bvid: str, json_dir: str = "Data") -> List[Dict]:
    """
    加载带时间戳的字幕文件
    """
    json_path = os.path.join(json_dir, f"{bvid}_subtitle.json")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"未找到字幕文件: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def find_subtitle_at_time(subtitles: List[Dict], time_seconds: float) -> Optional[Dict]:
    """
    根据时间（秒）查找对应的字幕
    """
    for sub in subtitles:
        if sub['from'] <= time_seconds <= sub['to']:
            return sub
    return None

def load_danmaku(danmaku_file: str) -> pd.DataFrame:
    """
    加载弹幕数据
    CSV格式: bvid, video_title, video_time_sec, text 等
    """
    if not os.path.exists(danmaku_file):
        raise FileNotFoundError(f"未找到弹幕文件: {danmaku_file}")
    
    return pd.read_csv(danmaku_file)

def match_danmaku_with_subtitle(danmaku_file: str, bvid: str, output_file: Optional[str] = None):
    """
    将弹幕与字幕进行时间对应
    """
    
    try:
        subtitles = load_subtitle(bvid)
        danmaku_df = load_danmaku(danmaku_file)
    except FileNotFoundError as e:
        return None
    
    
    results = []
    for idx, row in danmaku_df.iterrows():
        danmaku_time = row['video_time_sec']
        danmaku_content = row['text']
        
        matched_subtitle = find_subtitle_at_time(subtitles, danmaku_time)
        
        result = {
            'danmaku_time': danmaku_time,
            'danmaku_content': danmaku_content,
            'subtitle_content': matched_subtitle['content'] if matched_subtitle else None,
            'subtitle_from': matched_subtitle['from'] if matched_subtitle else None,
            'subtitle_to': matched_subtitle['to'] if matched_subtitle else None,
        }
        
        for col in danmaku_df.columns:
            if col not in ['video_time_sec', 'text']:
                result[f'danmaku_{col}'] = row[col]
        
        results.append(result)
    
    result_df = pd.DataFrame(results)
    
    if output_file:
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    matched_count = result_df['subtitle_content'].notna().sum()
    match_rate = matched_count / len(result_df) * 100 if len(result_df) > 0 else 0
    
    return result_df, matched_count, match_rate

def analyze_danmaku_by_subtitle(result_df: pd.DataFrame):
    """
    按字幕内容分组分析弹幕
    """
    if result_df is None or result_df.empty:
        return
    
    subtitle_groups = result_df[result_df['subtitle_content'].notna()].groupby('subtitle_content')
    
    danmaku_counts = subtitle_groups.size().sort_values(ascending=False).head(10)
    for subtitle, count in danmaku_counts.items():
        pass

def find_high_engagement_moments(result_df: pd.DataFrame, window_seconds: float = 5):
    """
    找出弹幕高峰时段（高互动时刻）
    """
    if result_df is None or result_df.empty:
        return
    
    result_df = result_df.sort_values('danmaku_time')
    
    time_windows = []
    for i in range(0, int(result_df['danmaku_time'].max()) + 1, int(window_seconds)):
        window_end = i + window_seconds
        count = len(result_df[(result_df['danmaku_time'] >= i) & (result_df['danmaku_time'] < window_end)])
        
        if count > 0:
            window_subs = result_df[
                (result_df['danmaku_time'] >= i) & 
                (result_df['danmaku_time'] < window_end) &
                (result_df['subtitle_content'].notna())
            ]['subtitle_content'].unique()
            
            time_windows.append({
                'time_start': i,
                'time_end': window_end,
                'danmaku_count': count,
                'subtitles': ' | '.join(window_subs[:2])
            })
    
    time_windows_df = pd.DataFrame(time_windows).sort_values('danmaku_count', ascending=False)

if __name__ == "__main__":
    danmaku_dir = "danmaku_results"
    subtitle_dir = "Data"
    output_dir = "matched_results"
    
    os.makedirs(output_dir, exist_ok=True)
    
    danmaku_files = glob.glob(os.path.join(danmaku_dir, "*.csv"))
    danmaku_files = [f for f in danmaku_files if not os.path.basename(f).startswith("all_")]
    
    print(f"发现 {len(danmaku_files)} 个弹幕文件")
    
    success_count = 0
    fail_count = 0
    total_matched = 0
    total_danmaku = 0
    
    for danmaku_file in danmaku_files:
        filename = os.path.basename(danmaku_file)
        bvid = filename.split('_')[0]
        
        try:
            result = match_danmaku_with_subtitle(
                danmaku_file=danmaku_file,
                bvid=bvid,
                output_file=os.path.join(output_dir, f"{bvid}_matched.csv")
            )
            
            if result is not None:
                result_df, matched_count, match_rate = result
                success_count += 1
                total_matched += matched_count
                total_danmaku += len(result_df)
                print(f"[OK] {bvid}: {matched_count}/{len(result_df)} ({match_rate:.1f}%)")
            else:
                fail_count += 1
                print(f"[FAIL] {bvid}: 文件未找到")
        
        except Exception as e:
            fail_count += 1
            print(f"[ERROR] {bvid}: {str(e)}")
    
    print(f"\n处理完成:")
    print(f"成功: {success_count}, 失败: {fail_count}")
    print(f"总弹幕数: {total_danmaku}, 成功匹配: {total_matched}")
    if total_danmaku > 0:
        print(f"总体匹配率: {total_matched/total_danmaku*100:.1f}%")

