"""Company-wise LeetCode question lists.

These lists are tables, not prose, and users want them complete and in order
("all Adobe questions", "top 10 Google questions from the last 6 months").
Vector search would return only a few loosely related rows, so this module
answers such requests with a direct lookup in the CSV files instead of RAG.
"""
import csv
import re
from pathlib import Path

WINDOWS = {
    "6months": "last 6 months",
    "1year": "last 1 year",
    "2year": "last 2 years",
    "alltime": "all time",
}
ALIASES = {"meta": "facebook", "fb": "facebook", "jp-morgan": "jpmorgan"}
CUE_WORDS = {"question", "questions", "problem", "problems", "asked", "leetcode", "list"}
NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
                "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}


def _find_data_dir():
    for path in Path("notes").rglob("*_alltime.csv"):
        return path.parent
    return None


DATA_DIR = _find_data_dir()
COMPANIES = {}      # slug -> {window: path}
if DATA_DIR:
    for f in DATA_DIR.glob("*.csv"):
        slug, _, window = f.stem.rpartition("_")
        if window in WINDOWS:
            COMPANIES.setdefault(slug, {})[window] = f


def _display(slug):
    return slug.replace("-", " ").title()


def _find_company(text):
    """Return the company slug mentioned in the text (longest match wins)."""
    words = " ".join(re.findall(r"[a-z0-9]+", text.lower()))
    padded = f" {words} "
    candidates = {slug: slug.replace("-", " ") for slug in COMPANIES}
    for alias, target in ALIASES.items():
        if target in COMPANIES:
            candidates[target + "|" + alias] = alias.replace("-", " ")
    best = None
    for key, phrase in candidates.items():
        if f" {phrase} " in padded and (best is None or len(phrase) > len(best[1])):
            best = (key.split("|")[0], phrase)
    return best[0] if best else None


def _parse_window(text):
    t = text.lower()
    m = re.search(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")\s*(month|months|year|years|yr|yrs)\b", t)
    months = None
    if m:
        n = int(m.group(1)) if m.group(1).isdigit() else NUMBER_WORDS[m.group(1)]
        months = n * (12 if m.group(2).startswith(("year", "yr")) else 1)
    elif re.search(r"\b(last|past|this)\s+year\b", t):
        months = 12
    elif re.search(r"\b(recent|recently|latest)\b", t):
        months = 6
    if months is None:
        return "alltime"
    if months <= 6:
        return "6months"
    if months <= 12:
        return "1year"
    return "2year" if months <= 24 else "alltime"


def _parse_limit(text):
    t = re.sub(r"\b(\d+|" + "|".join(NUMBER_WORDS) + r")\s*(months?|years?|yrs?)\b", " ", text.lower())
    m = (re.search(r"\btop\s+(\d{1,3})\b", t)
         or re.search(r"\b(\d{1,3})\s+(?:[a-z]+\s+){0,2}?(?:questions?|problems?)\b", t))
    return int(m.group(1)) if m else None


def _parse_difficulty(text):
    for level in ("easy", "medium", "hard"):
        if re.search(rf"\b{level}\b", text.lower()):
            return level.title()
    return None


def _load(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            title = (row.get("Title") or "").strip()
            link = (row.get("Leetcode Question Link") or "").strip()
            if not title or not link.startswith("https://leetcode.com/"):
                continue
            try:
                freq = float(row.get("Frequency") or 0)
            except ValueError:
                freq = 0.0
            rows.append({"title": title, "link": link, "difficulty": (row.get("Difficulty") or "").strip(), "freq": freq})
    return sorted(rows, key=lambda r: r["freq"], reverse=True)


def company_list_reply(question):
    """Return a markdown list for 'give me <company> questions' requests, else None."""
    if not COMPANIES:
        return None
    tokens = set(re.findall(r"[a-z]+", question.lower()))
    if not tokens & CUE_WORDS:
        return None
    slug = _find_company(question)
    if not slug:
        return None

    window = _parse_window(question)
    note = ""
    if window not in COMPANIES[slug]:
        note = f"No {WINDOWS[window]} list exists for {_display(slug)}, so this is the all-time list.\n\n"
        window = "alltime"

    rows = _load(COMPANIES[slug][window])
    difficulty = _parse_difficulty(question)
    if difficulty:
        rows = [r for r in rows if r["difficulty"] == difficulty]
    total = len(rows)
    limit = _parse_limit(question)
    if limit:
        rows = rows[:limit]
    if not rows:
        return f"{note}I couldn't find matching questions for {_display(slug)}."

    scope = f"top {len(rows)} of {total}" if limit and limit < total else f"{total} questions"
    level = f", {difficulty} only" if difficulty else ""
    lines = [f"{_display(slug)} ({WINDOWS[window]}{level}): {scope}, most frequent first\n"]
    for i, r in enumerate(rows, 1):
        lines.append(f"{i}. [{r['title']}]({r['link']}) ({r['difficulty']})")
    return note + "\n".join(lines)
