"""
STEP 1: Search Bilibili Videos and Create Index
Usage: python step1_search_videos.py
Output: video_index.csv (contains BV号, title, author, views, etc.)
"""

import requests
import pandas as pd
import json
import time
import hashlib
import sys
from urllib.parse import urlencode
from functools import reduce

# Fix Windows console encoding
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# ==================== Configuration ====================
SEARCH_KEYWORD = "K签证"           # Search keyword
MIN_VIEWS = 5000                # Minimum play count
MAX_VIDEOS = 1000
SEARCH_ORDER = "click"
SEARCH_DURATION = 0
OUTPUT_FILE = "video_index.csv"

# Your Bilibili Cookie
BILIBILI_COOKIE = "_uuid=97C37C67-C191-510FB-131E-D92D7A2C1F10A61322infoc; b_nut=1750773460; bili_jct=4782a1bd8c4998f79c2b024eefcb39b5; bili_ticket=eyJhbGciOiJIUzI1NiIsImtpZCI6InMwMyIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjIzOTUyNDEsImlhdCI6MTc2MjEzNTk4MSwicGx0IjotMX0.eFHZDtZajkYo1VQVSkcMBoK_N8L1flkEQ2ecqNRdX6k; bili_ticket_expires=1762395181; bp_t_offset_483182659=1130038442839769088; browser_resolution=1920-918; buvid_fp=15456629f94a63f07a7cb681251200f7; buvid3=BD945E14-BBF5-DD46-EED6-07C99C038B4F60669infoc; buvid4=BC8401F8-D588-3507-09E1-E360128730B203701-024062413-kwM%2FsWtmCPWa%2F%2BJOW7T6uQ%3D%3D; CURRENT_FNVAL=4048; CURRENT_QUALITY=112; DedeUserID=483182659; DedeUserID__ckMd5=b7c4f64253faf2cf; enable_feed_channel=ENABLE; enable_web_push=DISABLE; header_theme_version=OPEN; hit-dyn-v2=1; home_feed_column=5; LIVE_BUVID=AUTO1017344934582882; rpdid=|(u)~lkRl|m)0J'u~umkJ~)uJ; SESSDATA=5ab1212e%2C1765470578%2C43aa7%2A62CjAwWHNe_t3Z9qR96rU-564ypfCZo46j6xVs5irihn-bxUec8b_DrMMQjISs7YNXgYYSVm1qdER3Y0x1OVJaZENSTnRNeS1pdVVSekZJbERBSEVVbFk1TEdhWnRzZENOYmFpYkdMZmY2Y00xbXplTFBYalFmRjBrWUlGaEU5VHEyX0Y4ektUU01nIIEC; sid=8s0xjs9x; theme-avatar-tip-show=SHOWED; theme-tip-show=SHOWED; bmg_af_switch=1; bmg_src_def_domain=i1.hdslb.com"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com/",
    "Cookie": BILIBILI_COOKIE
}

# ==================== WBI Functions ====================
mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

def getMixinKey(orig: str):
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]

def encWbi(params: dict, img_key: str, sub_key: str):
    mixin_key = getMixinKey(img_key + sub_key)
    curr_time = round(time.time())
    params['wts'] = curr_time
    params = dict(sorted(params.items()))
    params = {k: ''.join(filter(lambda chr: chr not in "!'()*", str(v))) for k, v in params.items()}
    query = urlencode(params)
    wbi_sign = hashlib.md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = wbi_sign
    return params

def getWbiKeys():
    try:
        response = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers)
        data = response.json()
        if data.get('code') == 0:
            wbi_img = data['data']['wbi_img']['img_url'].split('/')[-1].split('.')[0]
            wbi_sub = data['data']['wbi_img']['sub_url'].split('/')[-1].split('.')[0]
            return wbi_img, wbi_sub
    except:
        pass
    return None, None

# ==================== Search Function ====================
def search_videos(keyword, min_views, max_results, order, duration):
    """Search videos and return list"""
    print(f"\n{'='*70}")
    print(f"BILIBILI VIDEO SEARCH")
    print(f"{'='*70}")
    print(f"Keyword: '{keyword}'")
    print(f"Min Views: {min_views:,}")
    print(f"Max Results: {max_results}")
    print(f"Order By: {order}")
    print(f"{'='*70}\n")
    
    # Get WBI keys
    print("[STEP 1] Getting WBI keys...")
    wbi_img_key, wbi_sub_key = getWbiKeys()
    if wbi_img_key and wbi_sub_key:
        print(f"[SUCCESS] WBI keys obtained")
    else:
        print(f"[WARN] Could not get WBI keys, search may fail")
    
    videos = []
    page = 1
    
    print(f"\n[STEP 2] Starting search...")
    
    while len(videos) < max_results:
        search_params = {
            'search_type': 'video',
            'keyword': keyword,
            'order': order,
            'duration': duration,
            'page': page,
            'page_size': 30
        }
        
        if wbi_img_key and wbi_sub_key:
            search_params = encWbi(search_params, wbi_img_key, wbi_sub_key)
        
        search_api = f"https://api.bilibili.com/x/web-interface/wbi/search/type?{urlencode(search_params)}"
        
        print(f"\n[PAGE {page}] Searching...")
        
        try:
            response = requests.get(search_api, headers=headers, timeout=15)
            data = response.json()
            
            if data.get('code') != 0:
                print(f"[ERROR] API error: {data.get('message')}")
                break
            
            result_list = data.get('data', {}).get('result', [])
            
            if not result_list:
                print(f"[INFO] No more results")
                break
            
            for item in result_list:
                bvid = item.get('bvid', '')
                title = item.get('title', '').replace('<em class="keyword">', '').replace('</em>', '')
                author = item.get('author', '')
                play = item.get('play', 0)
                video_review = item.get('video_review', 0)  # danmaku count
                duration_str = item.get('duration', '')
                pubdate = item.get('pubdate', 0)
                
                # Parse play count
                if isinstance(play, str):
                    if '万' in play:
                        play = int(float(play.replace('万', '')) * 10000)
                    else:
                        play = int(play.replace(',', '')) if play else 0
                
                # Filter by views
                if play >= min_views:
                    videos.append({
                        'bvid': bvid,
                        'title': title,
                        'author': author,
                        'play_count': play,
                        'danmaku_count': video_review,
                        'duration': duration_str,
                        'pubdate': pubdate,
                        'url': f"https://www.bilibili.com/video/{bvid}",
                        'crawled': 0  # Status: 0=not crawled, 1=success, -1=failed
                    })
                    print(f"  [{len(videos):3d}] {title[:45]:<45} | Views: {play:>8,} | BV: {bvid}")
                    
                    if len(videos) >= max_results:
                        break
            
            page += 1
            time.sleep(1.5)  # Rate limiting
            
        except Exception as e:
            print(f"[ERROR] Search failed: {e}")
            break
    
    return videos

# ==================== Cookie Validation ====================
def validate_cookie():
    """Validate Bilibili Cookie"""
    if not BILIBILI_COOKIE or BILIBILI_COOKIE.strip() == "":
        print("\n" + "="*70)
        print("[ERROR] 未设置 Cookie")
        print("="*70)
        print("\n请先设置 BILIBILI_COOKIE：")
        print("1. 运行 'python get_cookie_guide.py' 查看详细步骤")
        print("2. 或者手动获取：登录 bilibili.com -> F12 -> Network -> 复制 Cookie")
        print("3. 将 Cookie 粘贴到 search.py 第 24 行的 BILIBILI_COOKIE 中")
        return False
    
    try:
        response = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=headers)
        data = response.json()
        
        if data.get('code') == 0:
            user_data = data.get('data', {})
            print(f"\n[AUTH] 已登录: {user_data.get('uname', 'N/A')} (UID: {user_data.get('mid', 'N/A')})")
            return True
        else:
            print("\n" + "="*70)
            print("[ERROR] Cookie 无效或已过期")
            print("="*70)
            print(f"错误: {data.get('message')}")
            print("\n请更新 Cookie：")
            print("运行 'python get_cookie_guide.py' 查看详细步骤")
            return False
    except Exception as e:
        print(f"\n[WARN] Cookie 验证失败: {e}")
        return False

# ==================== Main ====================
def main():
    # Validate Cookie first
    if not validate_cookie():
        return
    
    # Search videos
    videos = search_videos(
        keyword=SEARCH_KEYWORD,
        min_views=MIN_VIEWS,
        max_results=MAX_VIDEOS,
        order=SEARCH_ORDER,
        duration=SEARCH_DURATION
    )
    
    if not videos:
        print("\n[ERROR] No videos found!")
        return
    
    # Save to CSV
    print(f"\n{'='*70}")
    print(f"[STEP 3] Saving results...")
    print(f"{'='*70}")
    
    df = pd.DataFrame(videos)
    df.to_csv(OUTPUT_FILE, encoding='utf-8-sig', index=False)
    
    print(f"\n[SUCCESS] Video index saved: {OUTPUT_FILE}")
    print(f"Total videos: {len(videos)}")
    print(f"\nColumn description:")
    print(f"  - bvid: Video ID (required for step 2)")
    print(f"  - title: Video title")
    print(f"  - author: Uploader name")
    print(f"  - play_count: View count")
    print(f"  - danmaku_count: Estimated danmaku count")
    print(f"  - duration: Video duration")
    print(f"  - url: Video URL")
    print(f"  - crawled: Status (0=pending, 1=done, -1=failed)")
    
    print(f"\n{'='*70}")
    print(f"NEXT STEP: Run 'python step2_crawl_danmaku.py' to crawl danmaku")
    print(f"{'='*70}")
    
    # Preview
    print(f"\n[PREVIEW] Top 5 videos:")
    print(df[['bvid', 'title', 'play_count', 'danmaku_count']].head().to_string(index=False))

if __name__ == "__main__":
    main()