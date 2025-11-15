import requests
import pandas as pd
from lxml import etree
import json
import time
import os
import re
import random
import sys
from datetime import datetime


if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# ==================== Configuration ====================
INPUT_FILE = "video_index.csv"
OUTPUT_DIR = "danmaku_results"
SAVE_INDIVIDUAL = True
SAVE_MERGED = True
CONTINUE_FROM_LAST = True

# Enhanced delay settings (INCREASED)
MIN_DELAY = 8                           # Minimum seconds between videos (increased from 3)
MAX_DELAY = 15                          # Maximum seconds between videos (increased from 6)
MAX_RETRIES = 5                         # More retries
RETRY_BASE_DELAY = 30                   # Base delay for exponential backoff (increased)

# Your Bilibili Cookie (UPDATED with SESSDATA)
BILIBILI_COOKIE = "_uuid=97C37C67-C191-510FB-131E-D92D7A2C1F10A61322infoc; b_nut=1750773460; bili_jct=4782a1bd8c4998f79c2b024eefcb39b5; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjIzOTUyNDEsImlhdCI6MTc2MjEzNTk4MSwicGx0IjotMX0.eFHZDtZajkYo1VQVSkcMBoK_N8L1flkEQ2ecqNRdX6k; bili_ticket_expires=1762395181; bp_t_offset_483182659=1130038442839769088; browser_resolution=1920-918; buvid_fp=15456629f94a63f07a7cb681251200f7; buvid3=BD945E14-BBF5-DD46-EED6-07C99C038B4F60669infoc; buvid4=BC8401F8-D588-3507-09E1-E360128730B203701-024062413-kwM%2FsWtmCPWa%2F%2BJOW7T6uQ%3D%3D; CURRENT_FNVAL=4048; CURRENT_QUALITY=112; DedeUserID=483182659; DedeUserID__ckMd5=b7c4f64253faf2cf; enable_feed_channel=ENABLE; enable_web_push=DISABLE; header_theme_version=OPEN; hit-dyn-v2=1; home_feed_column=5; LIVE_BUVID=AUTO1017344934582882; rpdid=|(u)~lkRl|m)0J'u~umkJ~)uJ; SESSDATA=5ab1212e%2C1765470578%2C43aa7%2A62CjAwWHNe_t3Z9qR96rU-564ypfCZo46j6xVs5irihn-bxUec8b_DrMMQjISs7YNXgYYSVm1qdER3Y0x1OVJaZENSTnRNeS1pdVVSekZJbERBSEVVbFk1TEdhWnRzZENOYmFpYkdMZmY2Y00xbXplTFBYalFmRjBrWUlGaEU5VHEyX0Y4ektUU01nIIEC; sid=8s0xjs9x; theme-avatar-tip-show=SHOWED; theme-tip-show=SHOWED; bmg_af_switch=1; bmg_src_def_domain=i1.hdslb.com"

# User-Agent rotation list
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
]

def get_headers():
    """Generate headers with random User-Agent"""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Referer": "https://www.bilibili.com/",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.bilibili.com",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "Cookie": BILIBILI_COOKIE
    }

# ==================== Danmaku Mode Mapping ====================
DANMAKU_MODES = {
    '1': 'Scroll',
    '4': 'Bottom',
    '5': 'Top',
    '6': 'Reverse',
    '7': 'Position',
    '8': 'Advanced',
    '9': 'BAS/Hidden'
}

# ==================== Crawl Function ====================
def crawl_video_danmaku(bvid, video_title, video_idx, total_videos):
    """Crawl danmaku with enhanced anti-detection"""
    print(f"\n[{video_idx}/{total_videos}] {bvid} | {video_title[:50]}...")
    
    # Method 1: Try to get CID from video page
    try:
        video_url = f"https://www.bilibili.com/video/{bvid}"
        response = requests.get(video_url, headers=get_headers(), timeout=20)
        cid_match = re.search(r'"cid":(\d+)', response.text)
        
        if not cid_match:
            print(f"  [ERROR] Could not extract cid")
            return None, "no_cid"
        
        cid = cid_match.group(1)
        print(f"  [INFO] CID: {cid}")
        
    except Exception as e:
        print(f"  [ERROR] Failed to get CID: {e}")
        return None, "cid_error"
    
    # Method 2: Try XML API with exponential backoff
    danmaku_data = []
    
    for attempt in range(MAX_RETRIES):
        try:
            # Add small random delay before each attempt
            if attempt > 0:
                # Exponential backoff: 30s, 60s, 120s, 240s, 480s
                wait_time = RETRY_BASE_DELAY * (2 ** attempt)
                print(f"  [RETRY {attempt + 1}/{MAX_RETRIES}] Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"  [API] Fetching danmaku...")
                # Small random delay to look more human
                time.sleep(random.uniform(1, 3))
            
            xml_api = f"https://api.bilibili.com/x/v1/dm/list.so?oid={cid}"
            response = requests.get(xml_api, headers=get_headers(), timeout=20)
            
            if response.status_code == 412:
                print(f"  [WARN] Rate limited (412)")
                if attempt == MAX_RETRIES - 1:
                    print(f"  [ERROR] Max retries reached, trying alternative method...")
                    # Fallback: try segment API
                    return try_segment_api(cid, bvid, video_title)
                continue
            
            if response.status_code == 200:
                try:
                    xml = etree.fromstring(response.content)
                    d_elements = xml.xpath("/i/d")
                    
                    for d in d_elements:
                        p_attribute = d.get('p')
                        text = d.text
                        if p_attribute and text:
                            p_parts = p_attribute.split(',')
                            mode = p_parts[1] if len(p_parts) > 1 else 'unknown'
                            
                            danmaku_data.append({
                                'bvid': bvid,
                                'video_title': video_title,
                                'video_time_sec': float(p_parts[0]),
                                'mode': mode,
                                'mode_name': DANMAKU_MODES.get(mode, f'Unknown({mode})'),
                                'font_size': p_parts[2] if len(p_parts) > 2 else '',
                                'color': p_parts[3] if len(p_parts) > 3 else '',
                                'timestamp': int(p_parts[4]) if len(p_parts) > 4 else 0,
                                'pool': p_parts[5] if len(p_parts) > 5 else '',
                                'user_hash': p_parts[6] if len(p_parts) > 6 else '',
                                'dmid': p_parts[7] if len(p_parts) > 7 else '',
                                'text': text
                            })
                    
                    print(f"  [SUCCESS] Collected {len(danmaku_data)} danmaku")
                    
                    if danmaku_data:
                        df_temp = pd.DataFrame(danmaku_data)
                        mode_counts = df_temp['mode_name'].value_counts()
                        mode_str = ", ".join([f"{mode}: {count}" for mode, count in mode_counts.head(3).items()])
                        print(f"  [STATS] {mode_str}")
                        
                        hidden_count = len(df_temp[df_temp['mode'].isin(['8', '9'])])
                        if hidden_count > 0:
                            print(f"  [HIDDEN] ★ {hidden_count} advanced/hidden danmaku!")
                    
                    return danmaku_data, "success"
                    
                except Exception as parse_error:
                    print(f"  [ERROR] Parse error: {parse_error}")
                    if attempt == MAX_RETRIES - 1:
                        return None, "parse_error"
                    continue
            else:
                print(f"  [WARN] HTTP {response.status_code}")
                if attempt == MAX_RETRIES - 1:
                    return None, f"http_{response.status_code}"
                continue
                
        except Exception as e:
            print(f"  [ERROR] Request failed: {e}")
            if attempt == MAX_RETRIES - 1:
                return None, "exception"
            continue
    
    return None, "max_retries"

def try_segment_api(cid, bvid, video_title):
    """Fallback: try segment API (less likely to be rate limited)"""
    print(f"  [FALLBACK] Trying segment API...")
    danmaku_data = []
    
    # Try first 3 segments (18 minutes of video)
    for segment in range(1, 4):
        try:
            time.sleep(random.uniform(2, 4))
            seg_api = f"https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid={cid}&segment_index={segment}"
            response = requests.get(seg_api, headers=get_headers(), timeout=20)
            
            if response.status_code == 200 and len(response.content) > 10:
                xml = etree.fromstring(response.content)
                d_elements = xml.xpath("//d")
                
                for d in d_elements:
                    p_attribute = d.get('p')
                    text = d.text
                    if p_attribute and text:
                        p_parts = p_attribute.split(',')
                        mode = p_parts[1] if len(p_parts) > 1 else 'unknown'
                        
                        danmaku_data.append({
                            'bvid': bvid,
                            'video_title': video_title,
                            'video_time_sec': float(p_parts[0]),
                            'mode': mode,
                            'mode_name': DANMAKU_MODES.get(mode, f'Unknown({mode})'),
                            'font_size': p_parts[2] if len(p_parts) > 2 else '',
                            'color': p_parts[3] if len(p_parts) > 3 else '',
                            'timestamp': int(p_parts[4]) if len(p_parts) > 4 else 0,
                            'pool': p_parts[5] if len(p_parts) > 5 else '',
                            'user_hash': p_parts[6] if len(p_parts) > 6 else '',
                            'dmid': p_parts[7] if len(p_parts) > 7 else '',
                            'text': text
                        })
                
                if d_elements:
                    print(f"  [SEGMENT {segment}] {len(d_elements)} danmaku")
        except:
            pass
    
    if danmaku_data:
        print(f"  [FALLBACK SUCCESS] Total: {len(danmaku_data)} danmaku")
        return danmaku_data, "success_fallback"
    else:
        return None, "fallback_failed"

# ==================== Main Process ====================
def main():
    print(f"\n{'='*70}")
    print(f"BILIBILI DANMAKU CRAWLER (Enhanced Anti-Detection)")
    print(f"{'='*70}")
    print(f"[CONFIG] Delay: {MIN_DELAY}-{MAX_DELAY}s per video")
    print(f"[CONFIG] Retry: {MAX_RETRIES} attempts with exponential backoff")
    print(f"{'='*70}")
    
    if not os.path.exists(INPUT_FILE):
        print(f"\n[ERROR] Input file not found: {INPUT_FILE}")
        return
    
    print(f"\n[STEP 1] Loading video index: {INPUT_FILE}")
    video_df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
    print(f"[INFO] Total videos: {len(video_df)}")
    
    if CONTINUE_FROM_LAST and 'crawled' in video_df.columns:
        pending_df = video_df[video_df['crawled'] != 1].copy()
        print(f"[INFO] Pending: {len(pending_df)} videos")
        if len(pending_df) == 0:
            print(f"[INFO] All done!")
            return
    else:
        pending_df = video_df.copy()
        pending_df['crawled'] = 0
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    print(f"\n{'='*70}")
    print(f"[STEP 2] Starting crawl (this will take a while)...")
    print(f"{'='*70}")
    
    all_danmaku = []
    success_count = 0
    failed_count = 0
    processed = 0
    
    for idx, row in pending_df.iterrows():
        bvid = row['bvid']
        title = row['title']
        processed += 1
        
        danmaku_data, status = crawl_video_danmaku(
            bvid=bvid,
            video_title=title,
            video_idx=processed,
            total_videos=len(pending_df)
        )
        
        if status in ["success", "success_fallback"] and danmaku_data:
            video_df.loc[video_df['bvid'] == bvid, 'crawled'] = 1
            success_count += 1
            all_danmaku.extend(danmaku_data)
            
            if SAVE_INDIVIDUAL:
                df_ind = pd.DataFrame(danmaku_data)
                safe_title = "".join(c for c in title[:40] if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{OUTPUT_DIR}/{bvid}_{safe_title}.csv"
                df_ind.to_csv(filename, encoding='utf-8-sig', index=False)
                print(f"  [SAVED] {os.path.basename(filename)}")
        else:
            video_df.loc[video_df['bvid'] == bvid, 'crawled'] = -1
            failed_count += 1
            print(f"  [FAILED] Reason: {status}")
        
        video_df.to_csv(INPUT_FILE, encoding='utf-8-sig', index=False)
        
        # Longer random delay to avoid detection
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        print(f"  [WAIT] {delay:.1f}s before next video...")
        time.sleep(delay)
    
    # Save results
    if SAVE_MERGED and all_danmaku:
        print(f"\n{'='*70}")
        print(f"[STEP 3] Saving merged results...")
        print(f"{'='*70}")
        
        df_all = pd.DataFrame(all_danmaku)
        merged_file = f"{OUTPUT_DIR}/all_danmaku_merged.csv"
        df_all.to_csv(merged_file, encoding='utf-8-sig', index=False)
        print(f"[SAVED] {merged_file}")
        
        df_hidden = df_all[df_all['mode'].isin(['8', '9'])]
        if not df_hidden.empty:
            hidden_file = f"{OUTPUT_DIR}/hidden_danmaku_only.csv"
            df_hidden.to_csv(hidden_file, encoding='utf-8-sig', index=False)
            print(f"[SAVED] {hidden_file} ({len(df_hidden)} hidden)")
    
    # Statistics
    print(f"\n{'='*70}")
    print(f"FINAL STATISTICS")
    print(f"{'='*70}")
    print(f"Processed: {success_count + failed_count} videos")
    print(f"  ✓ Success: {success_count}")
    print(f"  ✗ Failed: {failed_count}")
    print(f"Total danmaku: {len(all_danmaku):,}")
    
    if all_danmaku:
        df_all = pd.DataFrame(all_danmaku)
        print(f"\nMode distribution:")
        mode_counts = df_all['mode_name'].value_counts()
        for mode, count in mode_counts.items():
            pct = count / len(all_danmaku) * 100
            print(f"  {mode:20s}: {count:>8,} ({pct:>5.1f}%)")
        
        hidden_count = len(df_all[df_all['mode'].isin(['8', '9'])])
        if hidden_count > 0:
            print(f"\n★ Hidden danmaku: {hidden_count:,} ({hidden_count/len(all_danmaku)*100:.1f}%)")
    
    print(f"\n{'='*70}")
    print(f"[DONE] Results in: {OUTPUT_DIR}/")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()