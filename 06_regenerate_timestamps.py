import os
import sys
import time
import glob
import logging
import subprocess
from typing import Optional
import pandas as pd
import json

INPUT_CSV = "outputs/01_video_index/videos_without_subtitle.csv"

BASE_DIR = os.path.abspath(".")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
AUDIO_DIR = os.path.join(OUT_DIR, "04_audio_temp")
TXT_DIR = os.path.join(OUT_DIR, "05_transcripts")
JSON_DIR = os.path.join(OUT_DIR, "03_subtitles_json")
LOG_DIR = os.path.join(OUT_DIR, "logs")

MODEL_SIZE = "medium"
MAX_RETRIES = 3
SLEEP_BETWEEN = (3, 7)

YTDLP_TPL = os.path.join(AUDIO_DIR, "%(id)s.%(ext)s")
YTDLP_CMD = [
    "yt-dlp",
    "-x", "--audio-format", "mp3",
    "-o", YTDLP_TPL,
]

os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "regenerate_timestamps.log"),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
console.setFormatter(logging.Formatter("%(message)s"))
logging.getLogger("").addHandler(console)

def _rand_sleep(a: int, b: int):
    import random
    time.sleep(random.uniform(a, b))

def download_audio_by_bvid(bvid: str, url: str) -> Optional[str]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logging.info(f"下载音频（第 {attempt}/{MAX_RETRIES} 次）：{bvid}")
            cmd = YTDLP_CMD + [url]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                logging.warning(f"yt-dlp 失败：{proc.stderr.strip()[:500]}")
                _rand_sleep(*SLEEP_BETWEEN)
                continue
            pattern = os.path.join(AUDIO_DIR, f"{bvid}.*")
            candidates = glob.glob(pattern)
            if candidates:
                mp3s = [p for p in candidates if p.lower().endswith(".mp3")]
                return mp3s[0] if mp3s else candidates[0]
            else:
                newest = sorted(glob.glob(os.path.join(AUDIO_DIR, "*.mp3")), key=os.path.getmtime, reverse=True)
                if newest:
                    return newest[0]
        except Exception as e:
            logging.warning(f"下载异常：{e}")
        _rand_sleep(*SLEEP_BETWEEN)
    return None

def transcribe_with_timestamps(audio_path: str, model):
    import whisper
    logging.info(f"开始转录：{os.path.basename(audio_path)}")
    result = model.transcribe(
        audio_path,
        language="zh",
        verbose=False,
        initial_prompt="以下是一段中文视频的逐字转录。"
    )
    segments = result.get("segments", [])
    
    subtitles = []
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if text:
            subtitles.append({
                "from": seg.get("start", 0),
                "to": seg.get("end", 0),
                "content": text,
                "location": 2
            })
    
    return subtitles

def save_json(bvid: str, subtitles: list) -> str:
    out_path = os.path.join(JSON_DIR, f"{bvid}_subtitle.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(subtitles, f, ensure_ascii=False, indent=2)
    return out_path

def main():
    logging.info("=" * 60)
    logging.info("重新生成带时间戳的字幕文件")
    logging.info("=" * 60)
    
    try:
        import whisper
    except Exception:
        logging.error("未安装 openai-whisper，请先安装：pip install openai-whisper")
        sys.exit(1)
    
    if not os.path.exists(INPUT_CSV):
        logging.error(f"未找到输入 CSV：{INPUT_CSV}")
        sys.exit(1)
    
    df = pd.read_csv(INPUT_CSV)
    
    # 找出已经转录但没有JSON的视频
    need_regenerate = []
    for _, row in df.iterrows():
        bvid = str(row.get("bvid", "")).strip()
        if row.get("has_subtitle") == 1 and row.get("subtitle_method") == "whisper_txt":
            txt_file = os.path.join(TXT_DIR, f"{bvid}.txt")
            json_file = os.path.join(JSON_DIR, f"{bvid}_subtitle.json")
            
            if os.path.exists(txt_file) and not os.path.exists(json_file):
                need_regenerate.append(row)
    
    if not need_regenerate:
        logging.info("所有视频都已有带时间戳的字幕！")
        return
    
    logging.info(f"发现 {len(need_regenerate)} 个视频需要重新生成时间戳")
    
    # 加载模型
    logging.info(f"加载 Whisper 模型：{MODEL_SIZE}")
    model = whisper.load_model(MODEL_SIZE)
    
    processed = 0
    for idx, row in enumerate(need_regenerate):
        bvid = str(row.get("bvid", "")).strip()
        url = str(row.get("url", f"https://www.bilibili.com/video/{bvid}")).strip()
        title = str(row.get("title", "")).strip()
        
        logging.info("-" * 60)
        logging.info(f"[{idx+1}/{len(need_regenerate)}] 处理：{bvid} | {title[:60]}")
        
        # 下载音频
        audio_path = download_audio_by_bvid(bvid, url)
        if not audio_path or not os.path.exists(audio_path):
            logging.warning(f"{bvid} 音频下载失败，跳过")
            continue
        
        # 转录
        ok = False
        subtitles = []
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                subtitles = transcribe_with_timestamps(audio_path, model)
                ok = True
                break
            except Exception as e:
                logging.warning(f"转录失败（第 {attempt}/{MAX_RETRIES} 次）：{e}")
                _rand_sleep(*SLEEP_BETWEEN)
        
        if not ok:
            logging.warning(f"{bvid} 转录失败，跳过")
            continue
        
        # 保存JSON
        out_json = save_json(bvid, subtitles)
        logging.info(f"JSON 已保存：{out_json}（{len(subtitles)} 条字幕）")
        
        # 更新CSV
        df.loc[df["bvid"] == bvid, "subtitle_method"] = "whisper"
        df.to_csv(INPUT_CSV, index=False, encoding="utf-8-sig")
        
        # 删除临时音频
        try:
            os.remove(audio_path)
            logging.info("已删除临时音频文件")
        except Exception as e:
            logging.warning(f"删除音频失败：{e}")
        
        processed += 1
        _rand_sleep(*SLEEP_BETWEEN)
    
    logging.info("-" * 60)
    logging.info(f"任务完成：成功重新生成 {processed} 个视频的时间戳")
    logging.info("=" * 60)

if __name__ == "__main__":
    main()

