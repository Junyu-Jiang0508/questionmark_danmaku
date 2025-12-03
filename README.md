# questionmark_danmaku

**Computational Pipeline for Analyzing "Question Mark Storms" in the Digital Public Sphere**

> **📄 Manuscript & Theoretical Framework**
>
> The full theoretical background, research design, and empirical findings associated with this codebase are documented in the manuscript file:
> **`00000_Manual_Scripts.pdf`**
>
> Please refer to this document for the complete academic context regarding "Infrapolitics," "Oppositional Decoding," and the "K-Visa" case study.

---

## 1. Project Overview

This repository contains the end-to-end computational pipeline used to construct the dataset for the study **"Question Mark Storms: Infrapolitics and Oppositional Decoding in China's Digital Public Sphere."**

The project investigates **"question mark storms"** (dense bursts of `?` or `？？？` danmaku) on the Bilibili platform. Theoretically, these visual torrents are treated as digital micro-acts of **infrapolitics**—low-cost, high-context signals of skepticism that emerge when hegemonic state narratives clash with the lived reality of audiences.

To empirically test this phenomenon, this pipeline automates the construction of a granular, time-aligned panel dataset by:
1.  **Corpus Construction:** Retrieving video metadata and engagement metrics.
2.  **Multimodal Data Extraction:** Crawling danmaku streams and retrieving official subtitles.
3.  **Audio Transcription:** Utilizing **OpenAI Whisper** to generate high-fidelity transcripts for uncaptioned content.
4.  **Temporal Alignment:** Synchronizing danmaku timestamps with spoken narrative segments to model the immediate reaction to specific discourse.
5.  **Signal Filtering:** Isolating "question mark" tokens to operationalize the dependent variable (dissent intensity).

> **⚠️ Note**
> * This is a **code-only repository**. Due to copyright, platform terms of service, and privacy considerations, the raw video files and full danmaku datasets are not included.
> * Researchers must ensure their data collection complies with Bilibili’s policies and relevant data protection laws.

---

## 2. Methodological Pipeline

The scripts are numbered sequentially to reflect the data processing workflow, moving from raw data acquisition to the construction of an analysis-ready panel dataset.

### Phase I: Data Acquisition
* **`01_search.py`**
    **Corpus Sampling.** Systematically searches Bilibili based on keywords (e.g., "K-Visa") or specific uploaders. It applies inclusion criteria (e.g., >5,000 views) to generate a target list of Video IDs (BVIDs).

* **`02_danmakucrawling.py`**
    **Danmaku Extraction.** Crawls the full XML danmaku streams for identified videos, preserving essential metadata: anonymized User ID, content payload, and video playback timestamp (down to the millisecond).

* **`03_crawling_api.py`**
    **API Interface.** An alternative retrieval module utilizing Bilibili's API for structured metadata or supplemental comment data when direct scraping is insufficient.

### Phase II: Narrative Reconstruction
* **`04_get_subtitles.py`**
    **Subtitle Retrieval.** Attempts to fetch official closed captions (CC) provided by uploaders or the platform. This serves as the primary source for the "Narrative Context" variable.

* **`05_whisper_transcriber.py`**
    **ASR Transcription.** For videos lacking official captions, this script employs the **OpenAI Whisper** model (configurable for local Docker execution) to extract spoken audio and generate time-stamped text segments. This ensures zero data loss for user-generated content.

### Phase III: Data Alignment & Operationalization
* **`06_regenerate_timestamps.py`**
    **Temporal Normalization.** Cleans and standardizes timestamps across disparate sources (official subtitles vs. Whisper outputs), ensuring a consistent time unit (seconds) for subsequent matching.

* **`07_danmaku_subtitle_matching.py`**
    **Segment-Level Alignment.** The core processing step. It merges the textual narrative (subtitles) and audience response (danmaku) into a unified dataframe. Each danmaku is matched to the nearest narrative segment, enabling the analysis of *what* was said immediately prior to a user's reaction.

* **`08_filter_question_danmaku.py`**
    **Variable Operationalization.** Filters the aligned dataset to isolate the dependent variable: **"Question Mark Danmaku."** It detects pure symbol strings (e.g., `?`, `?????`) and mixed-character strings where punctuation functions as the dominant semantic carrier, preparing the final corpus for regression analysis.

---

## 3. Repository Structure

```text
questionmark_danmaku/
├── 00000_Manual_Scripts.pdf            # MANUSCRIPT: Theory, method, and results
├── 01_search.py                        # Corpus sampling and video ID retrieval
├── 02_danmakucrawling.py               # Raw danmaku stream extraction
├── 03_crawling_api.py                  # API-based metadata retrieval
├── 04_get_subtitles.py                 # Official subtitle downloader
├── 05_whisper_transcriber.py           # ASR transcription (OpenAI Whisper)
├── 06_regenerate_timestamps.py         # Timestamp normalization
├── 07_danmaku_subtitle_matching.py     # Alignment of narrative and response data
├── 08_filter_question_danmaku.py       # Operationalization of the "Question Mark" variable
├── check_gpu.py                        # Utility: CUDA/GPU availability check
├── docker-compose.yaml                 # Docker config for reproducible ASR environment
├── requirements.txt                    # Python dependencies
└── torchvision-0.20.1...whl            # Local wheel for Windows/CUDA compatibility
