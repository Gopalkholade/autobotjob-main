import csv
import html
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

from fetchers import ATS_FETCHERS, SESSION
from filters import is_early_career_job, is_eligible_location, is_target_domain_job

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SEEN_JOBS_FILE = "seen_jobs.json"
CSV_FILE = "slugs.csv"

# Timezone & cooldown parameters
IST = timezone(timedelta(hours=5, minutes=30))
SUMMARY_TARGET_HOUR_IST = 21   # 9:00 PM IST
SUMMARY_COOLDOWN_HOURS = 23    # Minimum elapsed hours before another summary can send


def load_companies_from_csv(file_path: str = CSV_FILE) -> list[dict]:
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found.")
        return []

    companies = []
    with open(file_path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            clean_row = {
                (k.strip() if k else ""): (v.strip() if v else "")
                for k, v in row.items()
            }

            platform = clean_row.get("ats_platform", "").lower()
            slug = clean_row.get("api_slug", "")
            company_name = clean_row.get("company_name", "")
            api_url = clean_row.get("api_url", "")
            early_focus_raw = clean_row.get("early_career_focus", "").lower()
            early_career_focus = early_focus_raw in ("true", "1", "yes", "y")

            if company_name and platform:
                companies.append(
                    {
                        "name": company_name,
                        "platform": platform,
                        "slug": slug,
                        "api_url": api_url,
                        "early_career_focus": early_career_focus,
                    }
                )
    return companies


def load_state(file_path: str = SEEN_JOBS_FILE) -> tuple[set, str]:
    if not os.path.exists(file_path):
        return set(), ""

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            if isinstance(data, dict):
                timestamp = data.get("last_summary_sent_at") or data.get("last_summary_date", "")
                return set(data.get("seen_ids", [])), timestamp
            elif isinstance(data, list):
                return set(data), ""
        except json.JSONDecodeError:
            return set(), ""
    return set(), ""


def save_state(file_path: str, seen_jobs: set, last_summary_sent_at: str):
    payload = {
        "last_summary_sent_at": last_summary_sent_at,
        "seen_ids": sorted(list(seen_jobs)),
    }
    temp_file = f"{file_path}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(temp_file, file_path)


def is_summary_due(last_summary_iso: str, now: datetime) -> bool:
    if now.hour < SUMMARY_TARGET_HOUR_IST:
        return False

    if not last_summary_iso:
        return True

    try:
        last_sent = datetime.fromisoformat(last_summary_iso)
        if last_sent.tzinfo is None:
            last_sent = last_sent.replace(tzinfo=IST)
        elapsed = now - last_sent
        return elapsed >= timedelta(hours=SUMMARY_COOLDOWN_HOURS)
    except (ValueError, TypeError):
        return True


def send_telegram_alert(message_html: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram secrets missing. Skipping alert.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_html,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        res = SESSION.post(url, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")


def process_target_company(target: dict) -> tuple[list[tuple[str, dict]], bool]:
    platform = target["platform"]
    slug = target["slug"]
    company_name = target["name"]
    api_url = target["api_url"]
    early_focus = target["early_career_focus"]

    fetcher = ATS_FETCHERS.get(platform)
    if not fetcher:
        return [], False

    try:
        jobs = fetcher(slug, custom_url=api_url)
    except Exception:
        return [], False

    matched = []
    for job in jobs:
        title = job.get("title", "")

        if not is_target_domain_job(title):
            continue

        if early_focus and not is_early_career_job(title):
            continue

        if not is_eligible_location(job["location"], job.get("is_remote", False), job.get("country", "")):
            continue

        matched.append((company_name, job))

    return matched, True


def main():
    companies = load_companies_from_csv(CSV_FILE)
    if not companies:
        print("No companies loaded. Please verify slugs.csv.")
        return

    seen_jobs, last_summary_sent_at = load_state(SEEN_JOBS_FILE)

    is_first_run = len(seen_jobs) == 0
    current_run_jobs = set()
    new_openings = []
    failed_targets = []

    # Parallel scraping across 25 concurrent threads
    with ThreadPoolExecutor(max_workers=25) as executor:
        future_to_company = {executor.submit(process_target_company, c): c for c in companies}
        for future in as_completed(future_to_company):
            company_data = future_to_company[future]
            try:
                results, ok = future.result()
                if not ok:
                    failed_targets.append(f"{company_data['name']} ({company_data['platform']})")
                for company_name, job in results:
                    current_run_jobs.add(job["id"])
                    if job["id"] not in seen_jobs:
                        seen_jobs.add(job["id"])
                        new_openings.append((company_name, job))
            except Exception:
                failed_targets.append(f"{company_data['name']} ({company_data['platform']})")

    now_ist = datetime.now(IST)

    # 1. Baseline initialization on empty seen_jobs
    if is_first_run:
        save_state(SEEN_JOBS_FILE, seen_jobs, last_summary_sent_at)
        send_telegram_alert(
            f"🚀 <b>Job Monitor Initialized</b>\n\n"
            f"• <b>Companies loaded:</b> {len(companies)}\n"
            f"• <b>Baseline jobs cataloged:</b> {len(current_run_jobs)}\n"
            f"Tracking active for Data/AI/ML roles in India & Remote."
        )
        return

    # 2. If new jobs were found, broadcast them
    if new_openings:
        BATCH_SIZE = 5
        for i in range(0, len(new_openings), BATCH_SIZE):
            batch = new_openings[i : i + BATCH_SIZE]
            message_lines = [f"🔔 <b>New Job Openings ({len(new_openings)} total)</b>\n"]
            for company, job in batch:
                safe_company = html.escape(company)
                safe_title = html.escape(job["title"])
                safe_location = html.escape(job["location"])
                safe_url = html.escape(job["url"] or "")
                remote_tag = " 🌐 <b>(Remote)</b>" if job.get("is_remote") else ""

                message_lines.append(
                    f"🏢 <b>{safe_company}</b>{remote_tag}\n"
                    f"📌 <b>Role:</b> {safe_title}\n"
                    f"📍 <b>Location:</b> {safe_location}\n"
                    f'🔗 <a href="{safe_url}">Apply Here</a>\n'
                )
            send_telegram_alert("\n".join(message_lines))
    else:
        # Confirmation ping when no new jobs are found
        time_str = now_ist.strftime('%I:%M %p IST')
        send_telegram_alert(
            f"✅ <b>Monitor Run Completed ({time_str})</b>\n"
            f"• Scanned: {len(companies)} companies\n"
            f"• Tracked pool: {len(current_run_jobs)} active positions\n"
            f"• New matches: <b>0</b>"
        )

    # 3. Daily Summary Report (triggers once a day at or past 9:00 PM IST)
    if is_summary_due(last_summary_sent_at, now_ist):
        failed_str = ", ".join(failed_targets[:6]) if failed_targets else "None"
        if len(failed_targets) > 6:
            failed_str += f" (+{len(failed_targets) - 6} more)"

        summary_msg = (
            f"📊 <b>Daily Automation Summary</b>\n"
            f"🕒 <i>{now_ist.strftime('%d %b %Y, %I:%M %p IST')}</i>\n\n"
            f"🏢 <b>Companies Scanned:</b> {len(companies)}\n"
            f"⚡ <b>Failed / Dead Slugs:</b> {len(failed_targets)} ({failed_str})\n"
            f"🎯 <b>Total Active Matches Tracked:</b> {len(current_run_jobs)}\n"
            f"🆕 <b>New Openings Found Today:</b> {len(new_openings)}\n\n"
            f"<i>Next summary scheduled tomorrow at ~9:00 PM IST.</i>"
        )
        send_telegram_alert(summary_msg)
        last_summary_sent_at = now_ist.isoformat()

    # Save state
    save_state(SEEN_JOBS_FILE, seen_jobs, last_summary_sent_at)


if __name__ == "__main__":
    main()
