#!/usr/bin/env python3
"""
parse_lyrics.py

Parses raw Genius .txt lyric files into:
  - cleaned .txt  (plain lyric lines only, no tags, no metadata)
  - .json sidecar (structured: title, artist, sections with type/label/lines)

Usage:
  # one-shot: process entire lyrics/ folder in place
  python3 parse_lyrics.py

  # explicit folder
  python3 parse_lyrics.py --folder /path/to/lyrics

  # specific files
  python3 parse_lyrics.py --files Bloodbuzz_Ohio.txt About_Today.txt

  # dry run (print parsed output, write nothing)
  python3 parse_lyrics.py --dry-run

  # debug logging
  python3 parse_lyrics.py --debug
"""

import re
import os
import sys
import json
import argparse
import logging
import glob
from pathlib import Path

# ── args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="Parse raw Genius lyric .txt files.")
parser.add_argument("--folder", default="lyrics", help="Folder to process (default: lyrics/)")
parser.add_argument("--files",  nargs="+",        help="Specific .txt files to process")
parser.add_argument("--dry-run",action="store_true", help="Print output, write nothing")
parser.add_argument("--debug",  action="store_true", help="Enable verbose logging")
args = parser.parse_args()

logging.basicConfig(format="[%(levelname)s] %(message)s",
                    level=logging.DEBUG if args.debug else logging.WARNING)
log = logging.getLogger(__name__)

def info(msg): print(msg)

# ── section type classifier ───────────────────────────────────────────────────
# Maps keywords in section labels to a canonical type.
SECTION_TYPES = [
    (r'verse',        "verse"),
    (r'chorus',       "chorus"),
    (r'pre.?chorus',  "pre-chorus"),
    (r'post.?chorus', "post-chorus"),
    (r'bridge',       "bridge"),
    (r'outro',        "outro"),
    (r'intro',        "intro"),
    (r'hook',         "hook"),
    (r'refrain',      "refrain"),
    (r'interlude',    "interlude"),
    (r'instrumental', "instrumental"),
    (r'spoken',       "spoken"),
    (r'skit',         "skit"),
]

def classify_section(label):
    low = label.lower()
    for pattern, stype in SECTION_TYPES:
        if re.search(pattern, low):
            return stype
    return "other"

# ── garbage line stripper ─────────────────────────────────────────────────────
GARBAGE_RE = re.compile(
    r'^\d+\s+Contributors?'   # "1 Contributor" / "6 Contributors"
    r'|^Contributors?'        # bare "Contributors"
    r'|Lyrics$'               # line ending in "Lyrics" (title artifact)
    r'|\d+Embed'              # trailing Embed artifact
, re.IGNORECASE)

SECTION_RE = re.compile(r'^\[(.+?)\]$')

def is_garbage_line(line):
    """True if the line is metadata/artifact noise, not a lyric."""
    if GARBAGE_RE.search(line):
        return True
    return False

def parse_file(filepath):
    """
    Parse a raw Genius .txt file.

    Returns a dict:
      {
        "title":    str,
        "artist":   str,
        "sections": [ {"type": str, "label": str, "lines": [str]} ],
        "all_lines": [str]   # flat list of lyric lines, no tags
      }
    """
    path = Path(filepath)
    raw  = path.read_text(encoding="utf-8").splitlines()
    log.debug("parse_file: %s  raw lines=%d", path.name, len(raw))

    # ── extract title and artist from lines 1-2 ───────────────────────────────
    title  = raw[0].strip() if len(raw) > 0 else path.stem
    artist = raw[1].strip() if len(raw) > 1 else ""
    log.debug("title=%r  artist=%r", title, artist)

    # ── strip header: everything up to and including the garbage line ─────────
    # The garbage line is line 3 (index 2), but may run long if there's
    # an annotation blurb. We drop everything before the first [Section] tag
    # that isn't itself the title/artist, skipping any annotation prose.
    body = raw[2:]  # skip title + artist

    # Find index of first section tag — everything before it is garbage/annotation
    first_section_idx = None
    for idx, line in enumerate(body):
        if SECTION_RE.match(line.strip()):
            first_section_idx = idx
            break

    if first_section_idx is None:
        # No section tags at all — treat whole body as one unlabelled section
        # after stripping the garbage line
        log.debug("No section tags found, treating as flat lyric block")
        body_clean = [l for l in body if not is_garbage_line(l)]
    else:
        # Drop everything before the first section tag (garbage + annotation blurb)
        dropped = body[:first_section_idx]
        log.debug("Dropping %d pre-section lines: %r", len(dropped),
                  [l[:60] for l in dropped])
        body_clean = body[first_section_idx:]

    # ── parse into sections ───────────────────────────────────────────────────
    sections   = []
    current    = None

    for line in body_clean:
        line = line.rstrip()

        m = SECTION_RE.match(line)
        if m:
            # Save previous section if it had any lines
            if current and current["lines"]:
                sections.append(current)
            label = m.group(1).strip()
            current = {
                "type":  classify_section(label),
                "label": label,
                "lines": []
            }
            log.debug("Section: [%s] -> type=%r", label, current["type"])
            continue

        # Skip residual garbage inside the body (shouldn't be much)
        if is_garbage_line(line):
            log.debug("Dropping garbage line: %r", line)
            continue

        # Blank lines mark section breathing room — skip inside parser,
        # the section structure carries that information
        if not line:
            continue

        if current is None:
            # Lines before any section tag in a file with no tags
            current = {"type": "other", "label": "", "lines": []}

        current["lines"].append(line)

    # Append last section
    if current and current["lines"]:
        sections.append(current)

    # ── flat line list (for .txt output and Pi scripts) ───────────────────────
    all_lines = []
    for section in sections:
        # Skip purely instrumental sections (no sung lines)
        if section["type"] == "instrumental":
            log.debug("Skipping instrumental section: %r", section["label"])
            continue
        all_lines.extend(section["lines"])

    log.debug("Parsed %d sections, %d lyric lines total", len(sections), len(all_lines))

    return {
        "title":    title,
        "artist":   artist,
        "sections": sections,
        "all_lines": all_lines,
    }

# ── writers ───────────────────────────────────────────────────────────────────
def write_txt(parsed, filepath):
    """Write clean plain-text lyric lines, one per line."""
    out = "\n".join(parsed["all_lines"]) + "\n"
    if args.dry_run:
        info(f"\n── CLEAN TXT: {filepath} ──\n{out}")
        return
    Path(filepath).write_text(out, encoding="utf-8")
    log.debug("Wrote clean txt: %s (%d bytes)", filepath, len(out))

def write_json(parsed, filepath):
    """Write structured JSON sidecar."""
    payload = {
        "title":    parsed["title"],
        "artist":   parsed["artist"],
        "sections": parsed["sections"],
    }
    out = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.dry_run:
        info(f"\n── JSON: {filepath} ──\n{out}\n")
        return
    Path(filepath).write_text(out, encoding="utf-8")
    log.debug("Wrote json: %s (%d bytes)", filepath, len(out))

# ── main ──────────────────────────────────────────────────────────────────────
def get_targets():
    if args.files:
        return [Path(f) for f in args.files]
    folder = Path(args.folder)
    if not folder.exists():
        print(f"ERROR: folder not found: {folder}")
        sys.exit(1)
    targets = sorted(folder.glob("*.txt"))
    # exclude .gitkeep and already-clean files (no section tags)
    targets = [t for t in targets if t.name != ".gitkeep"]
    return targets

targets = get_targets()
if not targets:
    print("No .txt files found to process.")
    sys.exit(0)

info(f"Parsing {len(targets)} file(s)...\n")

parsed_ok = 0
failed    = 0

for path in targets:
    log.debug("Processing: %s", path)
    try:
        parsed = parse_file(path)

        txt_path  = path                          # overwrite in place
        json_path = path.with_suffix(".json")     # sidecar alongside

        write_txt(parsed,  txt_path)
        write_json(parsed, json_path)

        line_count    = len(parsed["all_lines"])
        section_count = len(parsed["sections"])
        info(f"  ✓  {parsed['title']:<45}  {section_count:>2} sections  {line_count:>3} lines")
        parsed_ok += 1

    except Exception as e:
        info(f"  ✗  {path.name}  ERROR: {e}")
        log.debug("Exception on %s", path, exc_info=True)
        failed += 1

print(f"\nDone.  {parsed_ok} parsed  |  {failed} failed")
if args.dry_run:
    print("(dry run — no files written)")
