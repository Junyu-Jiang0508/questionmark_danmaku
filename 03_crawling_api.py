"""
Bilibili Danmaku Crawler using bilibili-api library
This is more stable and handles anti-bot mechanisms automatically
"""

from bilibili_api import video, sync, Credential
import pandas as pd
import time
import random
import os
import sys

# Fix Windows console encoding
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

# Delay settings (can be shorter with official API)
DELAY_MIN = 2
DELAY_MAX = 4

# Your Bilibili credentials (extract from browser cookies)
SESSDATA = "5ab1212e%2C1765470578%2C43aa7%2A62CjAwWHNe_t3Z9qR96rU-564ypfCZo46j6xVs5irihn-bxUec8b_DrMMQjISs7YNXgYYSVm1qdER3Y0x1OVJaZENSTnRNeS1pdVVSekZJbERBSEVVbFk1TEdhWnRzZENOYmFpYkdMZmY2Y00xbXplTFBYalFmRjBrWUlGaEU5VHEyX0Y4ektUU01nIIEC"
BILI_JCT = "4782a1bd8c4998f79c2b024eefcb39b5"
BUVID3 = "BD945E14-BBF5-DD46-EED6-07C99C038B4F60669infoc"

# Set credentials
credential = Credential(sessdata=SESSDATA, bili_jct=BILI_JCT, buvid3=BUVID3)

# Danmaku mode mapping
DANMAKU_MODES = {
    1: 'Scroll',
    4: 'Bottom',
    5: 'Top',
    6: 'Reverse',
    7: 'Position',
    8: 'Advanced',
    9: 'BAS/Hidden'
}

def crawl_video_danmaku_api(bvid, video_title, video_idx, total_videos):
    """Crawl danmaku using bilibili-api library"""
    print(f"\n[{video_idx}/{total_videos}] {bvid} | {video_title[:50]}...")
    
    try:
        # Create video object
        v = video.Video(bvid=bvid, credential=credential)
        
        # Get video info to find cid
        info = sync(v.get_info())
        cid = info['cid']
        
        print(f"  [INFO] CID: {cid}")
        
        # Get danmaku using correct method (pass page_index=0 for first page)
        danmaku_list = sync(v.get_danmakus(page_index=0))
        
        danmaku_data = []
        
        for dm in danmaku_list:
            # All attributes are now confirmed from test
            mode = dm.mode
            danmaku_data.append({
                'bvid': bvid,
                'video_title': video_title,
                'video_time_sec': dm.dm_time,
                'mode': str(mode),
                'mode_name': DANMAKU_MODES.get(mode, f'Unknown({mode})'),
                'font_size': dm.font_size,
                'color': dm.color,
                'timestamp': dm.send_time,
                'pool': dm.pool,
                'user_hash': dm.crc32_id,
                'dmid': dm.id_,
                'text': dm.text
            })
        
        print(f"  [SUCCESS] Collected {len(danmaku_data)} danmaku")
        
        # Show statistics
        if danmaku_data:
            df_temp = pd.DataFrame(danmaku_data)
            mode_counts = df_temp['mode_name'].value_counts()
            mode_str = ", ".join([f"{mode}: {count}" for mode, count in mode_counts.head(3).items()])
            print(f"  [STATS] {mode_str}")
            
            hidden_count = len(df_temp[df_temp['mode'].isin(['8', '9'])])
            if hidden_count > 0:
                print(f"  [HIDDEN] ★ {hidden_count} advanced/hidden danmaku!")
        
        return danmaku_data, "success"
        
    except Exception as e:
        print(f"  [ERROR] {str(e)}")
        return None, "failed"

def main():
    print("="*70)
    print("BILIBILI DANMAKU CRAWLER (Using bilibili-api library)")
    print("="*70)
    print(f"[CONFIG] Delay: {DELAY_MIN}-{DELAY_MAX}s per video")
    print("="*70)
    
    # Check input file
    if not os.path.exists(INPUT_FILE):
        print(f"\n[ERROR] {INPUT_FILE} not found")
        print("Please run search.py first!")
        return
    
    # Load video index
    print(f"\n[STEP 1] Loading video index: {INPUT_FILE}")
    video_df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
    print(f"[INFO] Total videos: {len(video_df)}")
    
    # Filter pending videos
    if CONTINUE_FROM_LAST and 'crawled' in video_df.columns:
        pending_df = video_df[video_df['crawled'] != 1].copy()
        print(f"[INFO] Pending: {len(pending_df)} videos")
        if len(pending_df) == 0:
            print("[INFO] All videos already crawled!")
            return
    else:
        pending_df = video_df.copy()
        pending_df['crawled'] = 0
    
    # Create output directory
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    # Start crawling
    print(f"\n{'='*70}")
    print(f"[STEP 2] Starting crawl...")
    print(f"{'='*70}")
    
    all_danmaku = []
    success_count = 0
    failed_count = 0
    processed = 0
    
    for idx, row in pending_df.iterrows():
        bvid = row['bvid']
        title = row['title']
        processed += 1
        
        # Crawl danmaku
        danmaku_data, status = crawl_video_danmaku_api(
            bvid=bvid,
            video_title=title,
            video_idx=processed,
            total_videos=len(pending_df)
        )
        
        # Update status
        if status == "success" and danmaku_data:
            video_df.loc[video_df['bvid'] == bvid, 'crawled'] = 1
            success_count += 1
            all_danmaku.extend(danmaku_data)
            
            # Save individual file
            if SAVE_INDIVIDUAL:
                df_ind = pd.DataFrame(danmaku_data)
                safe_title = "".join(c for c in title[:40] if c.isalnum() or c in (' ', '-', '_')).strip()
                filename = f"{OUTPUT_DIR}/{bvid}_{safe_title}.csv"
                df_ind.to_csv(filename, encoding='utf-8-sig', index=False)
                print(f"  [SAVED] {os.path.basename(filename)}")
        else:
            video_df.loc[video_df['bvid'] == bvid, 'crawled'] = -1
            failed_count += 1
        
        # Update index
        video_df.to_csv(INPUT_FILE, encoding='utf-8-sig', index=False)
        
        # Rate limiting
        delay = random.uniform(DELAY_MIN, DELAY_MAX)
        print(f"  [WAIT] {delay:.1f}s...")
        time.sleep(delay)
    
    # Save merged file
    if SAVE_MERGED and all_danmaku:
        print(f"\n{'='*70}")
        print(f"[STEP 3] Saving merged results...")
        print(f"{'='*70}")
        
        df_all = pd.DataFrame(all_danmaku)
        merged_file = f"{OUTPUT_DIR}/all_danmaku_merged.csv"
        df_all.to_csv(merged_file, encoding='utf-8-sig', index=False)
        print(f"[SAVED] {merged_file}")
        
        # Save hidden danmaku only
        df_hidden = df_all[df_all['mode'].isin(['8', '9'])]
        if not df_hidden.empty:
            hidden_file = f"{OUTPUT_DIR}/hidden_danmaku_only.csv"
            df_hidden.to_csv(hidden_file, encoding='utf-8-sig', index=False)
            print(f"[SAVED] {hidden_file} ({len(df_hidden)} hidden)")
    
    # Final statistics
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

