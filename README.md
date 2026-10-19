# Autobot Job Monitor

A lightweight Python job monitor that watches popular ATS job boards, filters for AI/ML/data roles, and sends Telegram alerts when fresh, relevant openings appear.

This project is tuned for India-focused hiring and remote-friendly opportunities, so it helps you catch early-career and mid-level data/AI roles without getting buried in senior, sales, or non-technical listings.

## What it does

- Scrapes jobs from multiple ATS platforms:
  - Greenhouse
  - Lever
  - Ashby
  - Workable
  - SmartRecruiters
- Filters for role titles matching data, AI, ML, analytics, and engineering keywords
- Excludes senior, management, and non-technical roles
- Keeps a seen-job state to avoid duplicate notifications
- Sends Telegram updates for:
  - new job alerts
  - daily summary reports
  - startup/monitor initialization status
- Supports India and global-remote role targeting

## Project layout

```text
.
├── fetchers.py        # ATS fetchers and HTTP session configuration
├── filters.py         # Role/location filtering logic
├── monitor.py         # Main orchestration, Telegram sending, and deduping
├── slugs.csv          # Companies + ATS metadata to monitor
├── seen_jobs.json     # Persisted seen job IDs
├── requirements.txt   # Python dependencies
├── README.md
└── .gitignore
```

## How the filter works

The app intentionally narrows candidates to roles that are likely relevant to data/AI careers:

- accepted keywords include: `data`, `ML`, `AI`, `analytics`, `python`, `software engineer`, `research engineer`, etc.
- rejected keywords include: `senior`, `manager`, `director`, `sales`, `recruiter`, `finance`, `marketing`, and similar non-technical roles
- remote and India-based locations are treated as eligible while clearly foreign-zone remote roles are filtered out
- early-career focus can be enabled from the CSV for specific companies and job tracks

## Setup

1. Create a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set Telegram environment variables:

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

On PowerShell:

```powershell
$env:TELEGRAM_BOT_TOKEN = "your_bot_token"
$env:TELEGRAM_CHAT_ID = "your_chat_id"
```

4. Update the companies list in `slugs.csv`.

Each row should include:

```csv
company_name,ats_platform,api_slug,api_url,early_career_focus
```

Example:

```csv
OpenAI,Ashby,openai,https://api.ashbyhq.com/posting-api/job-board/openai,True
```

## Run it

```bash
python monitor.py
```

The script will:

- load monitored companies from `slugs.csv`
- fetch active jobs from each ATS
- apply filters and dedupe logic
- send Telegram alerts when new relevant jobs appear
- keep a daily summary window for active listings

## Notes

- `seen_jobs.json` stores previously seen job IDs so the bot does not spam the same listing repeatedly.
- The monitor is meant to act like a job radar: useful for tracking active openings without manually checking multiple boards every day.
- You can tune filters in `filters.py` and company coverage in `slugs.csv` depending on your niche or location preference.

## Example Telegram alert

```text
🔔 New Job Openings (3 total)

🏢 OpenAI
📌 Role: Applied AI Engineer
📍 Location: Remote
🔗 Apply Here
```

## Why this is useful

Instead of spending time hunting through dozens of ATS pages, this bot does the boring part for you and only surfaces the kind of jobs you actually care about.

If you want, this project can also be extended with:

- a web dashboard
- email notifications
- SQL job storage
- more ATS integrations
- filtering by compensation, visa status, or work mode
