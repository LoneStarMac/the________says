import lyricsgenius
import requests
import time
import re
import os
import sys
import argparse
import logging
from bs4 import BeautifulSoup
from requests.exceptions import ConnectionError, Timeout
from dotenv import load_dotenv

# ── args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Download lyrics from Genius.")
parser.add_argument("--debug", action="store_true", help="Enable verbose logging")
parser.add_argument("--parse", action="store_true", help="Run parse_lyrics.py against downloaded files when done")
args = parser.parse_args()

# ── logging ───────────────────────────────────────────────────────────────────
log_level = logging.DEBUG if args.debug else logging.WARNING
logging.basicConfig(format="[%(levelname)s] %(message)s", level=log_level)
log = logging.getLogger(__name__)

def info(msg):
    print(msg)

# ── config ────────────────────────────────────────────────────────────────────
load_dotenv()
TOKEN      = os.getenv("GENIUS_TOKEN", "")
ARTIST     = "The National"
MAX_SONGS  = 400
OUTPUT_DIR = "lyrics"
RETRY_MAX  = 4
RETRY_WAIT = 5          # seconds, doubles each attempt

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
# ─────────────────────────────────────────────────────────────────────────────

if not TOKEN:
    print("ERROR: GENIUS_TOKEN not set.")
    print("       Copy .env.example to .env and add your token.")
    print("       Get one free at https://genius.com/api-clients")
    sys.exit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── helpers ───────────────────────────────────────────────────────────────────
def safe_filename(title):
    clean = re.sub(r'[^\w\s-]', '', title).strip()
    clean = re.sub(r'\s+', '_', clean)
    return clean + ".txt"

def scrape_lyrics(url, attempt=1):
    """
    Scrape lyrics directly from a Genius page URL.
    Uses div[data-lyrics-container="true"] — the current live selector.
    Retries on connection errors with exponential backoff.
    """
    log.debug("scrape_lyrics: fetching %s (attempt %d)", url, attempt)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except (ConnectionError, Timeout) as e:
        if attempt > RETRY_MAX:
            log.debug("scrape_lyrics: giving up after %d attempts", RETRY_MAX)
            return None
        wait = RETRY_WAIT * (2 ** (attempt - 1))
        info(f"        connection error, retrying in {wait}s (attempt {attempt}/{RETRY_MAX})...")
        log.debug("scrape_lyrics error: %s", e)
        time.sleep(wait)
        return scrape_lyrics(url, attempt + 1)
    except Exception as e:
        log.debug("scrape_lyrics unexpected error: %s", e)
        return None

    soup = BeautifulSoup(resp.text, "html.parser")
    containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})

    if not containers:
        log.debug("scrape_lyrics: no lyrics containers found at %s", url)
        return None

    lines = []
    for container in containers:
        # Replace <br> tags with newlines before extracting text
        for br in container.find_all("br"):
            br.replace_with("\n")
        # Each top-level block separated by a blank line
        lines.append(container.get_text())
        lines.append("")

    text = "\n".join(lines)
    # Collapse 3+ blank lines to 2
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    log.debug("scrape_lyrics: got %d lines from %s", len(text.splitlines()), url)
    return text

# ── connect (API only used for song discovery) ────────────────────────────────
info("Connecting to Genius API...")
genius = lyricsgenius.Genius(TOKEN, sleep_time=1.5, retries=3, timeout=15)
genius.verbose                = args.debug
genius.remove_section_headers = False
genius.skip_non_songs         = True

# ── fetch artist song list ────────────────────────────────────────────────────
info(f"Fetching song list for: {ARTIST}  (this may take a minute)...")
log.debug("search_artist(max_songs=%d, sort='title')", MAX_SONGS)

try:
    artist = genius.search_artist(ARTIST, max_songs=MAX_SONGS, sort="title",
                                  get_full_info=False)
except (ConnectionError, Timeout) as e:
    print(f"\nERROR: Could not reach Genius API while fetching song list.")
    print(f"       Check your connection and try again.")
    log.debug("search_artist failed: %s", e)
    sys.exit(1)

if not artist:
    print(f"ERROR: Artist '{ARTIST}' not found.")
    sys.exit(1)

total   = len(artist.songs)
saved   = 0
skipped = 0
failed  = 0

log.debug("Artist: %r  songs: %d", artist.name, total)
info(f"Found {total} songs. Scraping lyrics...\n")

# ── scrape lyrics ─────────────────────────────────────────────────────────────
for i, song in enumerate(artist.songs, 1):
    filename = safe_filename(song.title)
    filepath = os.path.join(OUTPUT_DIR, filename)

    # resume: skip files already on disk
    if os.path.exists(filepath):
        info(f"[{i:>3}/{total}]  –  already exists  ({song.title})")
        saved += 1
        continue

    if not song.url:
        info(f"[{i:>3}/{total}]  SKIP (no URL)  {song.title}")
        log.debug("No URL for song: %r", song.title)
        skipped += 1
        continue

    log.debug("[%d/%d] %r -> %s", i, total, song.title, song.url)
    lyrics = scrape_lyrics(song.url)

    if not lyrics:
        info(f"[{i:>3}/{total}]  SKIP (no lyrics scraped)  {song.title}")
        log.debug("scrape returned nothing for %r", song.title)
        skipped += 1
        continue

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"{song.title}\n")
            f.write(f"{song.artist}\n\n")
            f.write(lyrics)
            f.write("\n")
        log.debug("Wrote %d bytes to %s", os.path.getsize(filepath), filepath)
        info(f"[{i:>3}/{total}]  ✓  {song.title}")
        saved += 1
    except OSError as e:
        info(f"[{i:>3}/{total}]  ERROR writing file: {e}")
        log.debug("OSError: %s", e)
        failed += 1

    time.sleep(1.5)  # polite scraping delay

# ── summary ───────────────────────────────────────────────────────────────────
print(f"\nDone.  {saved} saved  |  {skipped} skipped  |  {failed} failed")
print(f"Output: ./{OUTPUT_DIR}/")
log.debug("Complete. saved=%d skipped=%d failed=%d total=%d", saved, skipped, failed, total)

# ── optional parse pass ───────────────────────────────────────────────────────
if args.parse:
    import subprocess
    parse_flags = ["--folder", OUTPUT_DIR]
    if args.debug:
        parse_flags.append("--debug")
    print(f"\nRunning parse_lyrics.py...")
    subprocess.run([sys.executable, "parse_lyrics.py"] + parse_flags)
