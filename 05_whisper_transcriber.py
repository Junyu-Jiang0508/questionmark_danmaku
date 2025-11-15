import os
import sys
import time
import glob
import logging
import subprocess
from typing import Optional
import pandas as pd

INPUT_CSV = "outputs/01_video_index/videos_without_subtitle.csv"

BASE_DIR = os.path.abspath(".")
OUT_DIR = os.path.join(BASE_DIR, "outputs")
AUDIO_DIR = os.path.join(OUT_DIR, "02_audio")
TXT_DIR = os.path.join(OUT_DIR, "05_transcripts")
JSON_DIR = os.path.join(OUT_DIR, "03_subtitles_json")
LOG_DIR = os.path.join(OUT_DIR, "logs")

MODEL_SIZE = "medium"     # tiny | base | small | medium | large
MAX_RETRIES = 3           # download/transcribe retries
SLEEP_BETWEEN = (3, 7)    # 各任务间随机休眠秒数区间
DELETE_AUDIO_AFTER = True # 转录成功后删除音频以省空间

# yt-dlp 模板
YTDLP_TPL = os.path.join(AUDIO_DIR, "%(id)s.%(ext)s")
YTDLP_CMD = [
    "yt-dlp",
    "-x", "--audio-format", "mp3",
    "-o", YTDLP_TPL,
]

# ==================== 日志设置 ====================
os.makedirs(AUDIO_DIR, exist_ok=True)
os.makedirs(TXT_DIR, exist_ok=True)
os.makedirs(JSON_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOG_DIR, "pipeline.log"),
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

def _check_command_exists(cmd: str) -> bool:
    try:
        subprocess.run([cmd, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        return True
    except FileNotFoundError:
        return False

def _ensure_dependencies():
    # yt-dlp
    if not _check_command_exists("yt-dlp"):
        logging.error("未检测到 yt-dlp，请先安装：pip install yt-dlp")
        sys.exit(1)
    # ffmpeg（yt-dlp 会调用）
    if not _check_command_exists("ffmpeg"):
        logging.error("未检测到 ffmpeg，请先安装（Mac: brew install ffmpeg | Ubuntu: apt-get install ffmpeg | Win: choco install ffmpeg）")
        sys.exit(1)
    # whisper / torch
    try:
        import whisper  # noqa
    except Exception:
        logging.error("未检测到 openai-whisper，请先安装：pip install openai-whisper")
        sys.exit(1)
    try:
        import torch  # noqa
    except Exception:
        logging.error("未检测到 torch，请先安装（根据平台选择正确版本），例如：pip install torch")
        sys.exit(1)

def _gpu_info_str() -> str:
    try:
        import torch
        if torch.cuda.is_available():
            dev = torch.cuda.get_device_name(0)
            return f"CUDA 可用：{dev}"
        return "CUDA 不可用，使用 CPU 转录"
    except Exception:
        return "无法检测 GPU，按 CPU 处理"

def download_audio_by_bvid(bvid: str, url: str) -> Optional[str]:
    """
    使用 yt-dlp 仅下载音频，返回音频路径（mp3）
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logging.info(f"开始下载音频（第 {attempt}/{MAX_RETRIES} 次）：{bvid}")
            cmd = YTDLP_CMD + [url]
            proc = subprocess.run(cmd, capture_output=True, text=True)
            if proc.returncode != 0:
                logging.warning(f"yt-dlp 失败：{proc.stderr.strip()[:500]}")
                _rand_sleep(*SLEEP_BETWEEN)
                continue
            # 依据 bvid 匹配下载的文件（yt-dlp 的 %(id)s 通常是 BV 号）
            pattern = os.path.join(AUDIO_DIR, f"{bvid}.*")
            candidates = glob.glob(pattern)
            if candidates:
                # 优先选 mp3
                mp3s = [p for p in candidates if p.lower().endswith(".mp3")]
                return mp3s[0] if mp3s else candidates[0]
            else:
                # 回退：找最新的 mp3
                newest = sorted(glob.glob(os.path.join(AUDIO_DIR, "*.mp3")), key=os.path.getmtime, reverse=True)
                if newest:
                    return newest[0]
        except Exception as e:
            logging.warning(f"下载异常：{e}")
        _rand_sleep(*SLEEP_BETWEEN)
    return None

def transcribe_with_timestamps(audio_path: str, model):
    """
    Whisper 转录，返回（纯文本、带时间戳的segments、段落数）
    """
    import whisper
    logging.info(f"开始转录：{os.path.basename(audio_path)}")
    result = model.transcribe(
        audio_path,
        language="zh",
        verbose=False,
        initial_prompt="以下是一段中文视频的逐字转录。"
    )
    segments = result.get("segments", [])
    
    # 纯文本：合并所有 segment 的 text
    lines = []
    # 带时间戳的字幕列表（兼容B站字幕格式）
    subtitles = []
    
    for seg in segments:
        text = str(seg.get("text", "")).strip()
        if text:
            lines.append(text)
            # 保存时间戳信息
            subtitles.append({
                "from": seg.get("start", 0),
                "to": seg.get("end", 0),
                "content": text,
                "location": 2  # B站字幕格式：2表示底部居中
            })
    
    plain_text = "\n".join(lines).strip()
    return plain_text, subtitles, len(lines)

def save_txt(bvid: str, text: str) -> str:
    out_path = os.path.join(TXT_DIR, f"{bvid}.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    return out_path

def save_json(bvid: str, subtitles: list) -> str:
    """保存带时间戳的JSON格式字幕（兼容B站字幕格式）"""
    import json
    out_path = os.path.join(JSON_DIR, f"{bvid}_subtitle.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(subtitles, f, ensure_ascii=False, indent=2)
    return out_path

def main():
    logging.info("=" * 60)
    logging.info("Whisper 纯文本批量转录启动")
    _ensure_dependencies()
    logging.info(_gpu_info_str())

    # 载入数据
    if not os.path.exists(INPUT_CSV):
        logging.error(f"未找到输入 CSV：{INPUT_CSV}")
        sys.exit(1)

    df = pd.read_csv(INPUT_CSV)
    # 兼容：若无 has_subtitle 列，则创建
    if "has_subtitle" not in df.columns:
        df["has_subtitle"] = 0
    if "subtitle_method" not in df.columns:
        df["subtitle_method"] = ""
    if "subtitle_count" not in df.columns:
        df["subtitle_count"] = 0

    # 筛未转录
    target = df[df["has_subtitle"] != 1].copy()
    logging.info(f"发现 {len(target)} 个无字幕视频")

    if target.empty:
        logging.info("无需处理：所有视频已有字幕。")
        return

    # 预加载模型一次，提升批量效率
    import whisper
    logging.info(f"加载 Whisper 模型：{MODEL_SIZE}（首次可能较慢）")
    model = whisper.load_model(MODEL_SIZE)

    processed = 0
    for idx, row in target.iterrows():
        bvid = str(row.get("bvid", "")).strip()
        url = str(row.get("url", f"https://www.bilibili.com/video/{bvid}")).strip()
        title = str(row.get("title", "")).strip()

        logging.info("-" * 60)
        logging.info(f"[{processed+1}/{len(target)}] 处理：{bvid} | {title[:60]}")

        audio_path = download_audio_by_bvid(bvid, url)
        if not audio_path or not os.path.exists(audio_path):
            logging.warning(f"{bvid} 音频下载失败，跳过。")
            continue

        # 转录（带重试）
        txt = ""
        subtitles = []
        seg_count = 0
        ok = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                txt, subtitles, seg_count = transcribe_with_timestamps(audio_path, model)
                ok = True
                break
            except Exception as e:
                logging.warning(f"转录失败（第 {attempt}/{MAX_RETRIES} 次）：{e}")
                _rand_sleep(*SLEEP_BETWEEN)
        if not ok:
            logging.warning(f"{bvid} 转录失败，跳过。")
            continue

        # 保存纯文本
        out_txt = save_txt(bvid, txt)
        logging.info(f"TXT 已保存：{out_txt}（段落数：{seg_count}）")
        
        # 保存带时间戳的JSON
        out_json = save_json(bvid, subtitles)
        logging.info(f"JSON 已保存：{out_json}（带时间戳）")

        # 更新 CSV
        df.loc[df["bvid"] == bvid, "has_subtitle"] = 1
        df.loc[df["bvid"] == bvid, "subtitle_method"] = "whisper"
        df.loc[df["bvid"] == bvid, "subtitle_count"] = seg_count
        df.to_csv(INPUT_CSV, index=False, encoding="utf-8-sig")

        # 删除音频（可选）
        if DELETE_AUDIO_AFTER:
            try:
                os.remove(audio_path)
                logging.info("已删除音频文件（节省空间）")
            except Exception as e:
                logging.warning(f"删除音频失败：{e}")

        processed += 1
        _rand_sleep(*SLEEP_BETWEEN)

    logging.info("-" * 60)
    logging.info(f"任务完成：成功处理 {processed} 个视频")
    logging.info("=" * 60)

if __name__ == "__main__":
    main()
