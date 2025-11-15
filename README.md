# questionmark_danmaku

**What this repo does (in one sentence):**  
End-to-end pipeline to **search Bilibili videos, crawl danmaku and subtitles, run Whisper transcription, and align “question-mark danmaku” (e.g. `????`) with the spoken content** for downstream discourse analysis.

This repository contains the core scripts I use to build a research corpus of **question-mark danmaku storms**—dense bursts of `?` bullet comments on Bilibili—by automatically:

1. Finding relevant videos,
2. Crawling their danmaku and subtitles,
3. Transcribing audio with Whisper when subtitles are missing, and
4. Matching danmaku timestamps to the nearest subtitle/transcript segments,
5. Filtering out only the **“question-mark” style danmaku** for further analysis.

> ⚠️ **Note**
>
> - This is a **code-only** repository: it contains the pipeline, **not** the full video/danmaku dataset.  
> - Data collection from Bilibili is subject to **copyright, platform policies, and local laws**; please use responsibly.

---

## 1. Project overview

### Why question-mark danmaku?

On Bilibili and similar platforms, strings of `?`, `？？？`, or mixed punctuation often function as:

- reactions of confusion or disbelief,
- subtle disagreement or mockery,
- or low-risk “micro-resistance” in sensitive contexts.

Rather than reading individual comments in isolation, this project focuses on **high-density “question-mark storms”** and asks:

- When do viewers collectively flood the screen with `?`?
- What is happening in the **audio / subtitles** at those moments?
- How do these storms relate to **political, social, or cultural content** in the videos?

This repository provides the **technical backbone** for building such a dataset.

---

## 2. Pipeline at a glance

The core scripts are numbered in the order you typically run them:

1. **`01_search.py`**  
   Search Bilibili (by keyword, uploader, etc.) and collect a list of **video IDs / URLs** to be processed.

2. **`02_danmakucrawling.py`**  
   Given a list of video IDs, crawl their **danmaku (bullet comments)** and save them with timestamps and basic metadata.

3. **`03_crawling_api.py`**  
   Additional / alternative crawling through APIs (e.g., structured interfaces for danmaku or metadata), depending on how you prefer to pull data.

4. **`04_get_subtitles.py`**  
   Try to download **official subtitles / captions** for each video where available (e.g., Bilibili generated or uploader-provided subtitles).

5. **`05_whisper_transcriber.py`**  
   For videos without usable subtitles, call **OpenAI Whisper** (or a local Whisper setup via Docker) to:
   - download the audio,
   - transcribe it into text,
   - and store it with time-aligned segments.

6. **`06_regenerate_timestamps.py`**  
   Clean and normalize timestamps from subtitles / transcripts so they can be reliably matched with danmaku times (e.g., fix offsets, ensure consistent time units).

7. **`07_danmaku_subtitle_matching.py`**  
   Core alignment step:
   - take danmaku (with timestamps) and subtitle / transcript segments,
   - match each danmaku to the **closest subtitle segment in time**,
   - produce a combined table linking: `video_id`, `danmaku_text`, `danmaku_time`, `subtitle_text`, `subtitle_time`.

8. **`08_filter_question_danmaku.py`**  
   Filter the merged dataset to keep only **“question-mark danmaku”**, e.g.:
   - pure `?` / `？？？`,
   - mixed patterns where `?` is dominant.  
   This produces the final **question-mark danmaku corpus** for later annotation or analysis.

Supporting files:

- **`manual_scripts.pdf`** – A manual walkthrough of the script sequence and expected inputs/outputs.  
- **`check_gpu.py`** – Quick utility to check whether GPU / CUDA is available (useful before running Whisper).  
- **`docker-compose.yaml`** – Optional Docker configuration (e.g. to spin up a local Whisper or environment).  
- **`requirements.txt`** – Python dependencies used by the pipeline.  
- **`torchvision-0.20.1+cu121-cp312-cp312-win_amd64.whl`** – Local wheel for installing the matching `torchvision` version in a Windows + CUDA 12.1 + Python 3.12 environment.

---

## 3. Repository structure

```text
questionmark_danmaku/
├── 01_search.py                     # Search Bilibili and collect video IDs
├── 02_danmakucrawling.py           # Crawl danmaku (bullet comments)
├── 03_crawling_api.py              # Additional API-based crawling
├── 04_get_subtitles.py             # Fetch official subtitles/captions
├── 05_whisper_transcriber.py       # Transcribe audio with Whisper
├── 06_regenerate_timestamps.py     # Clean/normalize timestamps
├── 07_danmaku_subtitle_matching.py # Align danmaku with subtitles/transcripts
├── 08_filter_question_danmaku.py   # Keep only “question-mark” danmaku
├── check_gpu.py                    # Utility: check GPU/CUDA availability
├── docker-compose.yaml             # Optional Docker config for environment/Whisper
├── manual_scripts.pdf              # Human-readable pipeline manual
├── requirements.txt                # Python dependencies
└── torchvision-0.20.1+cu121-...whl # Local torchvision wheel (Windows + CUDA 12.1)
