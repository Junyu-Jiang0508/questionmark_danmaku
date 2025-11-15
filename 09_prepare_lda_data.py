import json
import pandas as pd
import os
import jieba
import urllib.request

def download_stopwords():
    """下载并合并中文停用词"""
    urls = [
        "https://raw.githubusercontent.com/goto456/stopwords/master/cn_stopwords.txt",
        "https://raw.githubusercontent.com/goto456/stopwords/master/hit_stopwords.txt",
        "https://raw.githubusercontent.com/goto456/stopwords/master/baidu_stopwords.txt",
        "https://raw.githubusercontent.com/goto456/stopwords/master/scu_stopwords.txt"
    ]
    
    stopwords = set()
    for url in urls:
        try:
            response = urllib.request.urlopen(url)
            content = response.read().decode('utf-8')
            stopwords.update(content.strip().split('\n'))
        except:
            pass
    
    with open("stopwords_zh_combined.txt", 'w', encoding='utf-8') as f:
        f.write('\n'.join(sorted(stopwords)))
    
    return stopwords

def segment_text(text, stopwords):
    """中文分词，保留标点和表情符号"""
    words = jieba.cut(text)
    filtered_words = [w for w in words if w.strip() and w not in stopwords]
    return ' '.join(filtered_words)

def prepare_lda_data(analysis_file: str = "question_analysis/question_danmaku_analysis.json",
                     output_dir: str = "lda_analysis"):
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists("stopwords_zh_combined.txt"):
        stopwords = download_stopwords()
    else:
        with open("stopwords_zh_combined.txt", 'r', encoding='utf-8') as f:
            stopwords = set(f.read().strip().split('\n'))
    
    with open(analysis_file, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    subtitle_texts = []
    danmaku_texts = []
    combined_texts = []
    
    for result in results:
        subtitle_text = ' '.join([sub['content'] for sub in result['nearby_subtitles']])
        danmaku_text = ' '.join([str(dm.get('danmaku_content', '')) for dm in result['nearby_danmaku'] 
                                if pd.notna(dm.get('danmaku_content'))])
        
        if subtitle_text.strip():
            segmented_subtitle = segment_text(subtitle_text, stopwords)
            if segmented_subtitle.strip():
                subtitle_texts.append({
                    'doc_id': f"{result['bvid']}_{result['question_time']:.0f}",
                    'text': segmented_subtitle,
                    'bvid': result['bvid'],
                    'question_danmaku': result['question_danmaku']
                })
        
        if danmaku_text.strip():
            segmented_danmaku = segment_text(danmaku_text, stopwords)
            if segmented_danmaku.strip():
                danmaku_texts.append({
                    'doc_id': f"{result['bvid']}_{result['question_time']:.0f}",
                    'text': segmented_danmaku,
                    'bvid': result['bvid'],
                    'question_danmaku': result['question_danmaku']
                })
        
        combined_text = subtitle_text + ' ' + danmaku_text
        if combined_text.strip():
            segmented_combined = segment_text(combined_text, stopwords)
            if segmented_combined.strip():
                combined_texts.append({
                    'doc_id': f"{result['bvid']}_{result['question_time']:.0f}",
                    'text': segmented_combined,
                    'bvid': result['bvid'],
                    'question_danmaku': result['question_danmaku']
                })
    
    subtitle_df = pd.DataFrame(subtitle_texts)
    danmaku_df = pd.DataFrame(danmaku_texts)
    combined_df = pd.DataFrame(combined_texts)
    
    subtitle_df.to_csv(os.path.join(output_dir, "subtitle_texts.csv"), 
                      index=False, encoding='utf-8-sig')
    danmaku_df.to_csv(os.path.join(output_dir, "danmaku_texts.csv"), 
                     index=False, encoding='utf-8-sig')
    combined_df.to_csv(os.path.join(output_dir, "combined_texts.csv"), 
                      index=False, encoding='utf-8-sig')
    
    return subtitle_df, danmaku_df, combined_df

if __name__ == "__main__":
    subtitle_df, danmaku_df, combined_df = prepare_lda_data()

