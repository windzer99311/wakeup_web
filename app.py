import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI

# ---------------------------------------------------------------- config
BASE_DIR = Path(__file__).parent
WEBLIST_FILE = BASE_DIR / "weblist.txt"
CLICK_FILE = BASE_DIR / "click_count.txt"

CHECK_INTERVAL = 60          # seconds between each round
REQUEST_TIMEOUT = 20         # seconds per request
MAX_CONCURRENCY = 50         # parallel requests at once

# NOTE: these two values come from your browser session. If wake-up (resume)
# stops returning 204, grab fresh values from the browser's network tab.
CSRF_TOKEN = "bkZQYVV0RjN2RFEwVU1IY3lQSVJmVFV1V2Z2SmRUeWIndmgTEDIFRkVyJWEFFQcIPDxwMwMGIC8HXgJ6LGU+Fw=="
CSRF_COOKIE = "MTc5NTA1NzIzNnxJbE5VUVRSamExWkhVVE5WZWs1dVVsSlZSbWhRWVRCV2MwOVhSbXhWYmxaaFZVUm9NRTFGWjNoU00xVTlJZz09fP2dNXprQkuQcqe-TFyfRNIdRv35_LchRdhDp_eMg_NU"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36"
)

STATUS_NAMES = {
    10: "crashed",
    12: "sleeping",
    5: "running",
    0: "waking_up",
    2: "waking_up",
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("keepalive")

# ---------------------------------------------------------------- state
last_status: dict[str, dict] = {}     # latest result per website
file_lock = asyncio.Lock()


# ---------------------------------------------------------------- helpers
def normalize(line: str) -> str:
    line = line.strip().rstrip("/")
    if not line.startswith(("http://", "https://")):
        line = "https://" + line
    return line


def load_websites() -> list[str]:
    """Read weblist.txt (one site per line); ignores blanks, #comments, duplicates."""
    if not WEBLIST_FILE.exists():
        return []
    seen, sites = set(), []
    for raw in WEBLIST_FILE.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#"):
            continue
        site = normalize(raw)
        if site not in seen:
            seen.add(site)
            sites.append(site)
    return sites


def load_counts() -> dict[str, int]:
    try:
        return json.loads(CLICK_FILE.read_text() or "{}")
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_counts(counts: dict[str, int]) -> None:
    tmp = CLICK_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(counts, indent=2))
    tmp.replace(CLICK_FILE)           # atomic write


async def increment_click(site: str) -> None:
    async with file_lock:
        counts = load_counts()
        counts[site] = counts.get(site, 0) + 1
        save_counts(counts)


# ---------------------------------------------------------------- core logic
async def check_status(client: httpx.AsyncClient, site: str) -> int | None:
    r = await client.get(
        f"{site}/api/v2/app/status",
        headers={
            "sec-ch-ua-platform": '"Windows"',
            "user-agent": USER_AGENT,
            "accept": "application/json",
            "priority": "u=1, i",
        },
    )
    r.raise_for_status()
    return r.json().get("status")


async def click_button(client: httpx.AsyncClient, site: str) -> bool:
    r = await client.post(
        f"{site}/api/v2/app/resume",
        headers={
            "sec-ch-ua-platform": '"Windows"',
            "x-csrf-token": CSRF_TOKEN,
            "user-agent": USER_AGENT,
            "accept": "application/json, text/plain, */*",
            "sec-ch-ua-mobile": "?0",
            "origin": site,
            "priority": "u=1, i",
        },
        cookies={"_streamlit_csrf": CSRF_COOKIE},
    )
    return r.status_code == 204       # 204 == button clicked


async def process_site(client: httpx.AsyncClient, sem: asyncio.Semaphore, site: str) -> None:
    async with sem:
        info = {"status_code": None, "state": "unreachable", "woken": False,
                "checked_at": time.time()}
        try:
            code = await check_status(client, site)
            info["status_code"] = code
            info["state"] = STATUS_NAMES.get(code, f"unknown({code})")

            if code == 12:                                  # sleeping -> wake it
                if await click_button(client, site):
                    await increment_click(site)
                    info["woken"] = True
                    log.info("CLICKED wake-up button: %s", site)
                else:
                    log.warning("Wake-up click failed (not 204): %s", site)
        except Exception as e:
            info["error"] = str(e)
            log.warning("Error on %s: %s", site, e)
        last_status[site] = info


async def run_round() -> None:
    sites = load_websites()               # re-read each round: edits apply live
    if not sites:
        return
    sem = asyncio.Semaphore(MAX_CONCURRENCY)
    async with httpx.AsyncClient(verify=False, timeout=REQUEST_TIMEOUT) as client:
        await asyncio.gather(*(process_site(client, sem, s) for s in sites))
    log.info("Round done: %d sites checked", len(sites))


async def scheduler() -> None:
    while True:
        started = time.monotonic()
        try:
            await run_round()
        except Exception:
            log.exception("Round crashed")
        await asyncio.sleep(max(0, CHECK_INTERVAL - (time.monotonic() - started)))


# ---------------------------------------------------------------- app
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not CLICK_FILE.exists():
        CLICK_FILE.write_text("{}")
    task = asyncio.create_task(scheduler())
    yield
    task.cancel()


app = FastAPI(title="Streamlit Keep-Alive", lifespan=lifespan)


@app.get("/")
async def root():
    return {"sites": len(load_websites()), "interval_seconds": CHECK_INTERVAL}


@app.get("/click_count")
async def click_count():
    """{website: number_of_wake_up_clicks}; every site in weblist.txt is listed."""
    counts = load_counts()
    result = {site: counts.get(site, 0) for site in load_websites()}
    for site, n in counts.items():        # keep history of removed sites too
        result.setdefault(site, n)
    return result


@app.get("/status")
async def status():
    """Latest status seen for each website (bonus endpoint)."""
    return last_status
