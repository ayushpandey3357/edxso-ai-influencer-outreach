# Automated Micro-Influencer Outreach System

> **Production-Quality Prototype for EDXSO AI Engineer Intern Technical Assignment 1**

---

## Overview

The **Automated Micro-Influencer Outreach System** is an end-to-end, modular Python application designed to discover, filter, enrich, personalize, simulate sending, and track outreach for micro-influencers in the **Technology / AI / Developer** niche. The system integrates the official YouTube Data API v3, LLM-based structured personalization (Gemini / OpenAI), SQLite database tracking, and programmatic safety controls.

---

## Assignment Objective

Build an automated system that executes the complete influencer outreach lifecycle:
$$\text{Discovery} \longrightarrow \text{Data Collection} \longrightarrow \text{Enrichment} \longrightarrow \text{Filtering} \longrightarrow \text{AI Personalization} \longrightarrow \text{Outreach Simulation} \longrightarrow \text{Tracking} \longrightarrow \text{CSV Export}$$

Key requirements include retrieving at least 50 real candidate influencers for a test run, filtering by micro-influencer subscriber bounds ($5,000$ to $100,000$), calculating approximate engagement rates, extracting public contact emails strictly without guessing, generating personalized pitches and DMs based solely on verified data, preventing duplicate outreach via SQLite, and operating in a safe simulation mode.

---

## Data Authenticity & Safety

> **CRITICAL COMPLIANCE DIRECTIVE:**
> **"No fabricated influencer information, guessed email addresses, or fake engagement metrics are used."**

- **Zero Synthetic Data:** 100% of candidate channels, subscriber counts, view statistics, descriptions, and recent video titles are fetched live from the official YouTube Data API v3.
- **Strict Email Extraction:** Email addresses are **NEVER guessed or generated** (no `contact@...` or `hello@...`). Regex extraction is applied strictly to publicly listed channel and video descriptions. If no email is explicitly published, the field stores `"Not Found"`.
- **Safety-First Sending Layer:** Outbound emails are never dispatched automatically. The system defaults to `SIMULATE_SEND=true`.
- **Official API Usage:** Data discovery and enrichment are performed through the official YouTube Data API v3 rather than direct web scraping.
- **Zero Secrets Committed:** API keys are loaded strictly via environment variables (`.env`), which is ignored by `.gitignore`.

---

## Key Features & Pipeline

The system processes creators across **7 sequential pipeline stages**:

```
1. Discovery
   ↓
2. Data Collection & Enrichment
   ↓
3. Filtering
   ↓
4. AI Personalization
   ↓
5. Review / Validation
   ↓
6. Outreach Simulation
   ↓
7. Tracking / CSV Export
```

### Stage Summary
1. **Discovery:** Multi-query search across 16 configurable technology and AI queries with API pagination and channel ID deduplication to retrieve candidates up to `TARGET_DISCOVERY_COUNT` (default: 150).
2. **Data Collection & Enrichment:** Fetches channel statistics, uploads playlists, recent video performance metrics (views, likes, comments), extracts verified public emails via regex, and identifies content themes.
3. **Filtering:** Evaluates creators against configurable micro-influencer bounds (5,000–100,000 subscribers, $\ge 1.0\%$ engagement rate, and technology relevance). Every record receives a `filter_status` (`QUALIFIED` or `FAILED`) and a transparent `filter_reason`.
4. **AI Personalization:** Generates personalized **Email Collaboration Pitches (60–90 words)** and **Instagram DMs (15–30 words)** backed by programmatic word count validation, exponential backoff for 503 errors, 429 quota exhaustion handling, and a dynamic factual fallback generator.
5. **Review / Validation:** Programmatically checks generated message length and factual grounding before output.
6. **Outreach Simulation:** Safe execution layer checking SQLite database duplicates (`outreach_log`) and recording `SIMULATED`, `SKIPPED_NO_EMAIL`, or `SKIPPED_DUPLICATE` statuses.
7. **Tracking / CSV Export:** Generates structured CSV outputs (`influencers.csv`, `classified_influencers.csv`, `qualified_influencers.csv`, `personalized_outreach.csv`, `outreach_tracker.csv`) and maintains SQLite outreach log.

---

## Engagement Rate Methodology

YouTube Data API v3 does **not** provide a native single engagement rate field. Therefore, this system calculates an **approximate engagement rate proxy** across recent public videos:

```text
Video Engagement Rate = ((Likes + Comments) / Views) × 100

Channel Engagement Rate = Mean(Video Engagement Rates across recent videos)
```

### Data Handling Notes
- **Public Proxy:** This is an approximate engagement rate derived from public statistics.
- **Missing / Zero-View Handling:** If a channel has no recent public videos, zero total views, or missing statistics, `engagement_rate` is safely set to `"Not Found"` rather than zero to avoid distorting metrics.

---

## Discovery Queries List

The discovery module searches across 16 configurable queries defined in `Config.DISCOVERY_QUERIES`:

1. `AI tools`
2. `AI tutorial`
3. `generative AI`
4. `machine learning`
5. `artificial intelligence`
6. `Python tutorial`
7. `Python programming`
8. `software development`
9. `coding tutorial`
10. `developer tools`
11. `ChatGPT`
12. `LLM`
13. `AI agents`
14. `data science`
15. `technology`
16. `programming`

Channels are deduplicated strictly by `channel_id` across queries, and candidate target count is configurable via `TARGET_DISCOVERY_COUNT=150`.

---

## Project Structure

```
edxso_ai_influencer_outreach/
├── app/
│   ├── __init__.py           # Package initializer
│   ├── config.py             # Configuration & DISCOVERY_QUERIES definition
│   ├── youtube_client.py     # Official YouTube Data API v3 wrapper
│   ├── discovery.py          # Multi-query discovery & deduplication
│   ├── enrichment.py         # Profile enrichment, email regex & themes
│   ├── filtering.py          # Transparent micro-influencer classification
│   ├── personalization.py    # LLM pitch & DM generator with word validator & backoff
│   ├── outreach.py           # Simulated sending layer & duplicate check
│   ├── db.py                 # SQLite Database Manager (outreach_log)
│   └── pipeline.py           # 7-stage orchestrator & CSV exporter
├── data/                     # Output directory for CSV files & SQLite DB
│   └── .gitkeep
├── tests/                    # Pytest unit testing suite
│   ├── test_email_extraction.py
│   ├── test_engagement.py
│   ├── test_filtering.py
│   ├── test_deduplication.py
│   ├── test_word_count.py
│   ├── test_discovery_advanced.py
│   └── test_personalization_advanced.py
├── run.py                    # Main CLI entry point with PIPELINE SUMMARY
├── requirements.txt          # Dependencies
├── .env.example              # Environment variables template
├── .gitignore                # Git safety rules
└── README.md                 # Project documentation
```

---

## Environment Variables

Copy `.env.example` to `.env` and populate your API credentials:

```env
# YouTube Data API Credentials
YOUTUBE_API_KEY=your_youtube_api_key_here

# LLM Credentials
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
LLM_PROVIDER=gemini

OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini

# Configurable Thresholds
MIN_SUBSCRIBERS=5000
MAX_SUBSCRIBERS=100000
MIN_ENGAGEMENT_RATE=1.0

# Discovery Settings
TARGET_DISCOVERY_COUNT=150
RECENT_VIDEO_COUNT=5

# LLM Request Throttling
LLM_REQUEST_DELAY_SECONDS=2

# Safety Controls
SIMULATE_SEND=true
DB_PATH=data/outreach.db
```

---

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd edxso_ai_influencer_outreach
   ```
2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Testing

Automated tests are included and the latest verified local run completed with all collected tests passing:

```bash
pytest -q
```

Tests cover multi-query discovery, channel deduplication, subscriber filtering, engagement filtering, transparent pass/fail reasons, email regex extraction, word count validation (60–90w email, 15–30w DM), dynamic fallback generation, 429 quota handling, 503 backoff, and CSV exporting.

---

## Running the Pipeline

To execute the complete 7-stage pipeline:

```bash
python run.py
```

---

## Example Pipeline Output

> **Note:** The numbers below represent illustrative example console output. Actual results vary depending on YouTube search API results, quota availability, and filtering thresholds.

```text
============================================================
 AUTOMATED MICRO-INFLUENCER OUTREACH PIPELINE 
============================================================

[1/7] Discovering creators...
Searching query: 'AI tools'
Searching query: 'AI tutorial'
Discovered: 150 unique channels

[2/7] Enriching profiles...
Records saved: 150

[3/7] Filtering...
Filtering creators (Subscribers: 5,000-100,000, Min Engagement: 1.0%)...
Total Classified: 150 | Qualified: 14 | Failed: 136

[4/7] Generating AI messages...
Generated personalized messages for 14 qualified creators

[5/7] Creating tracker & checking database duplicates...
[6/7] Simulating sending...
Simulated Send Summary -> Simulated Sends: 2 | Skipped (No Email): 12 | Skipped (Duplicate): 0

[7/7] Exporting tracker...
Exported final tracker to data/outreach_tracker.csv

============================================
PIPELINE SUMMARY
============================================
Candidates discovered: 150
Profiles enriched: 150
Qualified: 14
Failed filtering: 136

LLM generated: 14
Fallback generated: 0
Generation failed: 0

Valid public emails: 2
No public email: 12

Simulated sends: 2
Duplicate skipped: 0
No-email skipped: 12

Tracker:
data/outreach_tracker.csv
============================================
```

---

## Latest Verified Run

The following results were recorded from the latest verified full local execution:

- **Candidates Discovered:** 193 unique channels
- **Profiles Enriched:** 193 profiles
- **Qualified Micro-Influencers:** 18 creators
- **Failed Filtering:** 175 creators
- **Valid Public Emails:** 3 creators (`aimasterytutorial@gmail.com`, `freelance.param@gmail.com`, `techaicenter2@gmail.com`)
- **Fallback Personalized Messages:** 18 creators (`generation_status=FALLBACK_SUCCESS`, `generation_provider=fallback`)
- **Simulated New Sends:** 1 send (`AI Mastery Tutorial`)
- **Duplicate Skipped:** 2 creators (prevented by SQLite `outreach.db` unique constraint)
- **No-Email Skipped:** 15 creators

---

## Error Handling & Resiliency

The system implements defensive error handling across all pipeline stages:

- **API Quota Exceeded:** Catches YouTube API HTTP 403 `quotaExceeded` errors and raises `QuotaExceededError` with clear terminal guidance.
- **503 UNAVAILABLE Handling:** Temporary server overload errors trigger exponential backoff retries with delays of 2s, 5s, and 10s.
- **429 Quota Exhaustion Handling:** When a 429 quota error (`RESOURCE_EXHAUSTED` or `insufficient_quota`) occurs, the system marks quota as exhausted and **stops repeatedly hammering the model**, transitioning remaining creators to dynamic fallback.
- **LLM Throttling:** Requests are throttled using `LLM_REQUEST_DELAY_SECONDS` (default: 2s) to remain within free-tier rate limits.
- **Dynamic Fallback Personalization:** If an LLM is unconfigured, unavailable, or out of quota, a dynamic factual generator produces pitches using verified creator data (name, recent video title, content themes, subscriber count, engagement rate).
- **Transparent Labeling:** Messages track `generation_status` (`SUCCESS`, `FALLBACK_SUCCESS`, `FAILED`) and `generation_provider` (`gemini`, `openai`, `mock`, `fallback`). Fallback messages are never falsely attributed to an LLM model.
- **Word Count Validation:** Programmatically validates email pitches ($60 \le w \le 90$) and Instagram DMs ($15 \le w \le 30$). Re-prompts the LLM with word count feedback on violations.

---

## Security & Privacy

1. **Git Exclusions:** `.env`, `*.db`, `__pycache__/`, `.pytest_cache/`, `.venv/`, and `data/*.csv` are ignored by `.gitignore`.
2. **Environment Variable Secret Management:** API credentials are loaded dynamically from environment variables; `.env.example` contains only non-sensitive placeholders.
3. **Simulation Mode Default:** Real email sending is disabled by default (`SIMULATE_SEND=true`).
4. **Data Integrity:** No email addresses are guessed or generated, and no creator statistics are fabricated.

---

## Scalability / Future Extensions

### Currently Implemented
- **API Request Batching:** Channel details and video statistics are fetched in optimal batches of 50 IDs per API call.
- **Channel Deduplication:** Candidate channel IDs are indexed in a set during discovery before enrichment to minimize API quota usage.
- **Modular Design:** Decoupled architecture separating API client, discovery, enrichment, filtering, AI personalization, database, and pipeline services.

### Possible Future Extensions
- **Multi-Platform Support:** Expanding discovery and enrichment to Twitch or X (Twitter).
- **Asynchronous Processing:** Integrating background task queues (e.g. Celery or Redis) for large-scale channel enrichment.
- **Database Scale-Up:** Transitioning from SQLite to PostgreSQL for multi-user outreach tracking.

---

## Assignment Requirement Mapping

| Requirement | Implementation Module | Verification Status |
| :--- | :--- | :--- |
| **50+ Real Influencers** | `app/discovery.py` | Discovered 193 candidate channels |
| **No Fabricated Data** | `app/enrichment.py` | Live YouTube Data API v3 metrics only |
| **Subscriber Bounds (5k–100k)** | `app/filtering.py` | Configurable in `app/config.py` |
| **Transparent Filter Reasons** | `app/filtering.py` | Explicit `PASS:` and `FAIL:` reasons in CSV |
| **Public Email Extraction** | `app/enrichment.py` | Strict regex only; `"Not Found"` if missing |
| **Content Themes** | `app/enrichment.py` | Keyword matching on real titles/descriptions |
| **60–90 Word Email Pitch** | `app/personalization.py` | Programmatic word count validation |
| **15–30 Word Instagram DM** | `app/personalization.py` | Programmatic word count validation |
| **Duplicate Prevention** | `app/db.py`, `app/outreach.py` | SQLite composite `UNIQUE(influencer_name, email)` |
| **Outreach Simulation Mode** | `app/outreach.py` | `SIMULATE_SEND=true` safety control |
| **CSV Outputs** | `app/pipeline.py` | 5 CSV datasets generated in `data/` |

---

## Limitations

- **Public Email Availability:** Many creators do not publish contact emails in public YouTube descriptions. Missing emails are correctly marked `"Not Found"` and skipped during outreach simulation.
- **API Quota Restrictions:** YouTube Data API v3 and LLM APIs operate under quota limits; the system uses request throttling, exponential backoff, and factual fallbacks to handle quota exhaustion gracefully.
- **Simulated Instagram Outreach:** Automated Instagram DM sending is simulated because direct automated DM dispatch is restricted by platform policies.
