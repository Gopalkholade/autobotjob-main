import requests

# Connection-pooled session tuned for fast I/O failover
SESSION = requests.Session()
adapter = requests.adapters.HTTPAdapter(pool_connections=35, pool_maxsize=35, max_retries=0)
SESSION.mount("https://", adapter)
SESSION.mount("http://", adapter)

SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
})

# Split timeout: 3.05s connect, 5s read
TIMEOUT = (3.05, 5)


def fetch_greenhouse_jobs(slug: str, custom_url: str = "") -> list[dict]:
    url = custom_url if custom_url else f"https://api.greenhouse.io/v1/boards/{slug}/jobs"
    identifier = slug or "custom"
    try:
        r = SESSION.get(url, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            jobs = []
            for job in data.get("jobs", []):
                loc_name = job.get("location", {}).get("name", "Unknown")
                jobs.append({
                    "id": f"gh_{identifier}_{job.get('id')}",
                    "title": job.get("title", "Untitled"),
                    "location": loc_name,
                    "url": job.get("absolute_url"),
                    "is_remote": "remote" in loc_name.lower(),
                    "country": "",
                })
            return jobs
    except Exception:
        pass
    return []


def fetch_lever_jobs(slug: str, custom_url: str = "") -> list[dict]:
    identifier = slug or "custom"
    jobs = []
    base_url = custom_url if custom_url else f"https://api.lever.co/v0/postings/{slug}?mode=json"
    offset = None
    pages_fetched = 0
    MAX_PAGES = 3

    try:
        while pages_fetched < MAX_PAGES:
            url = f"{base_url}&offset={offset}" if offset else base_url
            r = SESSION.get(url, timeout=TIMEOUT)
            if r.status_code != 200:
                break

            data = r.json()
            if not data or not isinstance(data, list):
                break

            for job in data:
                categories = job.get("categories", {})
                loc_name = categories.get("location", "Unknown")
                workplace_type = str(job.get("workplaceType", "")).lower()
                is_remote = (workplace_type == "remote") or ("remote" in loc_name.lower())
                country = job.get("country", "")

                jobs.append({
                    "id": f"lever_{identifier}_{job.get('id')}",
                    "title": job.get("text", "Untitled"),
                    "location": loc_name,
                    "url": job.get("hostedUrl"),
                    "is_remote": is_remote,
                    "country": country,
                })

            if len(data) >= 50:
                offset = data[-1].get("id")
                pages_fetched += 1
            else:
                break
    except Exception:
        pass

    return jobs


def fetch_ashby_jobs(slug: str, custom_url: str = "") -> list[dict]:
    url = custom_url if custom_url else f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    identifier = slug or "custom"
    try:
        r = SESSION.post(url, timeout=TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            jobs = []
            for job in data.get("jobs", []):
                loc_name = job.get("locationName", "Unknown")
                is_remote = bool(job.get("isRemote", False)) or ("remote" in loc_name.lower())
                jobs.append({
                    "id": f"ashby_{identifier}_{job.get('id')}",
                    "title": job.get("title", "Untitled"),
                    "location": loc_name,
                    "url": job.get("jobUrl"),
                    "is_remote": is_remote,
                    "country": "",
                })
            return jobs
    except Exception:
        pass
    return []


def fetch_workable_jobs(slug: str, custom_url: str = "") -> list[dict]:
    identifier = slug or "custom"
    jobs = []
    base_url = custom_url if custom_url else f"https://apply.workable.com/api/v1/widget/accounts/{slug}"
    next_token = None
    pages_fetched = 0
    MAX_PAGES = 3

    try:
        while pages_fetched < MAX_PAGES:
            params = {"token": next_token} if next_token else {}
            r = SESSION.get(base_url, params=params, timeout=TIMEOUT)
            if r.status_code != 200:
                break

            data = r.json()
            raw_jobs = data.get("jobs", [])
            for job in raw_jobs:
                city = job.get("city")
                country = job.get("country", "")
                loc_parts = [p for p in [city, country] if p]
                loc_name = ", ".join(loc_parts) if loc_parts else "Unknown"

                is_telecommute = bool(job.get("telecommuting", False))
                is_remote = is_telecommute or ("remote" in loc_name.lower())

                jobs.append({
                    "id": f"workable_{identifier}_{job.get('shortcode', job.get('id'))}",
                    "title": job.get("title", "Untitled"),
                    "location": loc_name,
                    "url": job.get("url") or job.get("shortlink"),
                    "is_remote": is_remote,
                    "country": country,
                })

            next_token = data.get("next_page")
            if not next_token or not raw_jobs:
                break
            pages_fetched += 1
    except Exception:
        pass

    return jobs


def fetch_smartrecruiters_jobs(slug: str, custom_url: str = "") -> list[dict]:
    identifier = slug or "custom"
    jobs = []
    base_url = custom_url if custom_url else f"https://api.smartrecruiters.com/v1/companies/{slug}/postings"
    offset = 0
    limit = 100
    pages_fetched = 0
    MAX_PAGES = 3

    try:
        while pages_fetched < MAX_PAGES:
            params = {"offset": offset, "limit": limit}
            r = SESSION.get(base_url, params=params, timeout=TIMEOUT)
            if r.status_code != 200:
                break

            data = r.json()
            content = data.get("content", [])
            for job in content:
                loc_obj = job.get("location", {})
                city = loc_obj.get("city")
                country = loc_obj.get("country", "")
                loc_parts = [p for p in [city, country] if p]
                loc_name = ", ".join(loc_parts) if loc_parts else "Unknown"

                is_remote = bool(loc_obj.get("remote", False)) or ("remote" in loc_name.lower())

                jobs.append({
                    "id": f"sr_{identifier}_{job.get('id')}",
                    "title": job.get("name", "Untitled"),
                    "location": loc_name,
                    "url": f"https://jobs.smartrecruiters.com/{slug}/{job.get('id')}",
                    "is_remote": is_remote,
                    "country": country,
                })

            total = data.get("totalFound", len(content))
            offset += limit
            pages_fetched += 1
            if offset >= total or not content:
                break
    except Exception:
        pass

    return jobs


ATS_FETCHERS = {
    "greenhouse": fetch_greenhouse_jobs,
    "lever": fetch_lever_jobs,
    "ashby": fetch_ashby_jobs,
    "workable": fetch_workable_jobs,
    "smartrecruiters": fetch_smartrecruiters_jobs,
    "smartrecruit": fetch_smartrecruiters_jobs,
}
