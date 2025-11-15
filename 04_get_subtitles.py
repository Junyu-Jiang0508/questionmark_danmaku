"""
B站视频字幕获取（API方法）
从video_index.csv批量获取官方字幕
"""

import requests
import pandas as pd
import json
import os
import time
import re
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# ==================== Configuration ====================
INPUT_FILE = "video_index.csv"
OUTPUT_DIR = "subtitles"
DELAY_MIN = 1
DELAY_MAX = 2

# Your Bilibili Cookie (UPDATED)
COOKIE = "_uuid=97C37C67-C191-510FB-131E-D92D7A2C1F10A61322infoc; b_nut=1750773460; bili_jct=4782a1bd8c4998f79c2b024eefcb39b5; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjIzOTUyNDEsImlhdCI6MTc2MjEzNTk4MSwicGx0IjotMX0.eFHZDtZajkYo1VQVSkcMBoK_N8L1flkEQ2ecqNRdX6k; bili_ticket_expires=1762395181; bp_t_offset_483182659=1130038442839769088; browser_resolution=1920-918; buvid_fp=15456629f94a63f07a7cb681251200f7; buvid3=BD945E14-BBF5-DD46-EED6-07C99C038B4F60669infoc; buvid4=BC8401F8-D588-3507-09E1-E360128730B203701-024062413-kwM%2FsWtmCPWa%2F%2BJOW7T6uQ%3D%3D; CURRENT_FNVAL=4048; CURRENT_QUALITY=112; DedeUserID=483182659; DedeUserID__ckMd5=b7c4f64253faf2cf; enable_feed_channel=ENABLE; enable_web_push=DISABLE; header_theme_version=OPEN; hit-dyn-v2=1; home_feed_column=5; LIVE_BUVID=AUTO1017344934582882; rpdid=|(u)~lkRl|m)0J'u~umkJ~)uJ; SESSDATA=5ab1212e%2C1765470578%2C43aa7%2A62CjAwWHNe_t3Z9qR96rU-564ypfCZo46j6xVs5irihn-bxUec8b_DrMMQjISs7YNXgYYSVm1qdER3Y0x1OVJaZENSTnRNeS1pdVVSekZJbERBSEVVbFk1TEdhWnRzZENOYmFpYkdMZmY2Y00xbXplTFBYalFmRjBrWUlGaEU5VHEyX0Y4ektUU01nIIEC; sid=8s0xjs9x; theme-avatar-tip-show=SHOWED; theme-tip-show=SHOWED; bmg_af_switch=1; bmg_src_def_domain=i1.hdslb.com"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Cookie": COOKIE
}

# Create output directory
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==================== Get CID from BV ====================
def get_cid_from_bvid(bvid):
    """从BV号获取CID"""
    try:
        url = f"https://www.bilibili.com/video/{bvid}"
        response = requests.get(url, headers=headers, timeout=15)
        
        cid_match = re.search(r'"cid":(\d+)', response.text)
        if cid_match:
            return cid_match.group(1)
        
        return None
    except Exception as e:
        print(f"  [ERROR] Failed to get CID: {e}")
        return None

# ==================== Get Bilibili Subtitle (API) ====================
def get_bilibili_subtitle(bvid, cid):
    """
    从B站API获取官方字幕
    
    返回格式：
    [
        {"from": 0.5, "to": 2.3, "location": 2, "content": "大家好"},
        ...
    ]
    """
    try:
        # Get player info
        url = "https://api.bilibili.com/x/player/v2"
        params = {'bvid': bvid, 'cid': cid}
        
        response = requests.get(url, params=params, headers=headers, timeout=15)
        data = response.json()
        
        if data.get('code') != 0:
            print(f"  [WARN] API error: {data.get('message')}")
            return None
        
        # Check for subtitles
        subtitle_info = data.get('data', {}).get('subtitle', {})
        subtitle_list = subtitle_info.get('subtitles', [])
        
        if not subtitle_list:
            print(f"  [INFO] No official subtitles")
            return None
        
        # Get first subtitle (usually Chinese)
        subtitle_url = subtitle_list[0].get('subtitle_url', '')
        if not subtitle_url.startswith('http'):
            subtitle_url = 'https:' + subtitle_url
        
        subtitle_lang = subtitle_list[0].get('lan', 'unknown')
        print(f"  [SUBTITLE] Found {subtitle_lang} subtitle")
        
        # Download subtitle content
        sub_response = requests.get(subtitle_url, timeout=15)
        subtitle_data = sub_response.json()
        
        subtitles = subtitle_data.get('body', [])
        print(f"  [SUCCESS] Got {len(subtitles)} subtitle lines")
        
        return subtitles
        
    except Exception as e:
        print(f"  [ERROR] Failed: {e}")
        return None

# ==================== Convert subtitle to text ====================
def subtitle_to_text(subtitles):
    """将字幕转换为纯文本"""
    if not subtitles:
        return ""
    
    lines = []
    for sub in subtitles:
        content = sub.get('content', '').strip()
        if content:
            lines.append(content)
    
    return '\n'.join(lines)

# ==================== Batch Processing ====================
def batch_get_subtitles():
    """批量获取video_index.csv中所有视频的字幕"""
    print("="*70)
    print("BILIBILI SUBTITLE BATCH DOWNLOADER")
    print("="*70)
    
    if not os.path.exists(INPUT_FILE):
        print(f"\n[ERROR] {INPUT_FILE} not found")
        return
    
    # Load video index
    print(f"\n[STEP 1] Loading video index: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
    print(f"[INFO] Total videos: {len(df)}")
    
    # Filter pending videos (if column exists)
    if 'has_subtitle' in df.columns:
        pending_df = df[df['has_subtitle'] != 1].copy()
        print(f"[INFO] Pending: {len(pending_df)} videos")
    else:
        pending_df = df.copy()
        df['has_subtitle'] = 0
        df['subtitle_method'] = 'none'
        df['subtitle_count'] = 0
    
    # Start processing
    print(f"\n{'='*70}")
    print(f"[STEP 2] Starting subtitle download...")
    print(f"{'='*70}")
    
    success_count = 0
    no_subtitle_count = 0
    error_count = 0
    processed = 0
    
    for idx, row in pending_df.iterrows():
        bvid = row['bvid']
        title = row.get('title', '')
        processed += 1
        
        print(f"\n[{processed}/{len(pending_df)}] {bvid} | {title[:50]}...")
        
        # Get CID
        cid = get_cid_from_bvid(bvid)
        if not cid:
            print(f"  [ERROR] Could not get CID")
            df.at[idx, 'has_subtitle'] = -1
            error_count += 1
            continue
        
        print(f"  [INFO] CID: {cid}")
        df.at[idx, 'cid'] = cid
        
        # Get subtitle
        subtitles = get_bilibili_subtitle(bvid, cid)
        
        if subtitles:
            # Save as JSON
            json_file = f"{OUTPUT_DIR}/{bvid}_subtitle.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(subtitles, f, ensure_ascii=False, indent=2)
            
            # Save as plain text
            txt_file = f"{OUTPUT_DIR}/{bvid}_subtitle.txt"
            text_content = subtitle_to_text(subtitles)
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write(text_content)
            
            # Update dataframe
            df.at[idx, 'has_subtitle'] = 1
            df.at[idx, 'subtitle_method'] = 'api'
            df.at[idx, 'subtitle_count'] = len(subtitles)
            
            success_count += 1
            print(f"  [SAVED] {json_file}")
            print(f"  [SAVED] {txt_file}")
        else:
            df.at[idx, 'has_subtitle'] = 0
            df.at[idx, 'subtitle_method'] = 'none'
            df.at[idx, 'subtitle_count'] = 0
            no_subtitle_count += 1
        
        # Save progress every 10 videos
        if processed % 10 == 0:
            df.to_csv(INPUT_FILE, index=False, encoding='utf-8-sig')
            print(f"  [PROGRESS] Saved")
        
        # Rate limiting
        import random
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        time.sleep(delay)
    
    # Final save
    df.to_csv(INPUT_FILE, index=False, encoding='utf-8-sig')
    
    # Statistics
    print(f"\n{'='*70}")
    print(f"FINAL STATISTICS")
    print(f"{'='*70}")
    print(f"Processed: {processed} videos")
    print(f"  ✓ Success: {success_count}")
    print(f"  ○ No subtitle: {no_subtitle_count}")
    print(f"  ✗ Error: {error_count}")
    print(f"Success rate: {success_count/processed*100:.1f}%")
    
    print(f"\n{'='*70}")
    print(f"[DONE] Results in: {OUTPUT_DIR}/")
    print(f"{'='*70}")

# ==================== Test Single Video ====================
def test_single_video(bvid=None):
    """测试单个视频"""
    if not bvid:
        # Use first video from index
        if os.path.exists(INPUT_FILE):
            df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
            bvid = df.iloc[0]['bvid']
        else:
            print("[ERROR] No video index found and no BV ID provided")
            return
    
    print("="*70)
    print(f"TESTING SUBTITLE DOWNLOAD")
    print("="*70)
    print(f"BV ID: {bvid}")
    
    # Get CID
    print(f"\n[STEP 1] Getting CID...")
    cid = get_cid_from_bvid(bvid)
    
    if not cid:
        print(f"[ERROR] Could not get CID")
        return
    
    print(f"[SUCCESS] CID: {cid}")
    
    # Get subtitle
    print(f"\n[STEP 2] Getting subtitle...")
    subtitles = get_bilibili_subtitle(bvid, cid)
    
    if subtitles:
        print(f"\n[SUCCESS] Got {len(subtitles)} subtitle lines")
        
        # Show first 5 lines
        print(f"\nFirst 5 subtitle lines:")
        for i, sub in enumerate(subtitles[:5]):
            print(f"  [{sub['from']:.1f}s - {sub['to']:.1f}s] {sub['content']}")
        
        # Save test result
        test_file = f"{OUTPUT_DIR}/test_{bvid}.json"
        with open(test_file, 'w', encoding='utf-8') as f:
            json.dump(subtitles, f, ensure_ascii=False, indent=2)
        
        test_txt = f"{OUTPUT_DIR}/test_{bvid}.txt"
        with open(test_txt, 'w', encoding='utf-8') as f:
            f.write(subtitle_to_text(subtitles))
        
        print(f"\n[SAVED] {test_file}")
        print(f"[SAVED] {test_txt}")
        
        return True
    else:
        print(f"\n[INFO] This video has no official subtitle")
        return False

# ==================== Main ====================
def main():
    import sys
    
    print("\n" + "="*70)
    print("B站字幕批量下载工具")
    print("="*70)
    
    # Check command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--test':
            # Test mode
            bvid = sys.argv[2] if len(sys.argv) > 2 else None
            test_single_video(bvid)
            return
        elif sys.argv[1] == '--batch':
            # Direct batch mode
            batch_get_subtitles()
            return
    
    # Default: test first then batch
    print("\n[TEST MODE] Testing with first video...")
    success = test_single_video()
    
    if success:
        print(f"\n{'='*70}")
        print("[AUTO] Test successful! Starting batch processing...")
        print(f"{'='*70}")
        batch_get_subtitles()
    else:
        print(f"\n[INFO] Test video has no subtitle")
        print("Note: Not all videos have official subtitles")
        print("Starting batch processing to find videos with subtitles...")
        batch_get_subtitles()

if __name__ == "__main__":
    main()

