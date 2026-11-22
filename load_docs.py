import re
from pathlib import Path
from pypdf import PdfReader

SUPPORTED = {".pdf", ".md", ".mdx", ".txt"}

# Folders and files that add noise, not knowledge
SKIP_DIRS = {"node_modules", "venv", "blog", "i18n", "translations", "_components",
             "experimental", "portal", "src", "_courses"}
SKIP_FILES = {"license.md", "contributing.md", "code_of_conduct.md", "changelog.md",
              "agents.md", "translations.md", "resume-old.md", "license.txt",
              "__template__.md"}

# --- patterns for the numbered study guide PDF ---
HEADER_NOISE = re.compile(r"CORE COMPUTER SCIENCE\s*/\s*STUDY GUIDE\s*\d*")
NUMBERED_HEADING = re.compile(
    r"^(\d+\.\d+\s+.+|\d+\.\s+[A-Z][A-Za-z &]{2,40}|.+ interview questions)$",
    re.MULTILINE,
)

# --- patterns for markdown / mdx ---
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
MD_HEADING = re.compile(r"^(#{1,4})\s+(.+?)\s*#*\s*$")
IMPORT_LINE = re.compile(r"^import .*$", re.MULTILINE)
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
HTML_TAGS = re.compile(r"</?(p|br|img|i|b|a|div|span|center|details|summary|sup|sub)\b[^>]*>", re.IGNORECASE)
# Sections that are only lists of links (no knowledge)
LINK_SECTION = re.compile(r"source\(s\)|sources|further reading|additional resources", re.IGNORECASE)


def should_skip(path, root):
    rel = path.relative_to(root)
    for part in rel.parts[:-1]:
        if part in SKIP_DIRS or part.startswith("."):
            return True
    name = path.name.lower()
    return name in SKIP_FILES or name.startswith("readme-")   # README-ja.md etc.


def load_file(path):
    """Read one file and return its text."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            reader = PdfReader(path)
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(f"Skipped {path.name}: {e}")
        return ""


def load_notes(folder):
    """Read every supported file in the folder, including subfolders."""
    root = Path(folder)
    docs = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED:
            continue
        if should_skip(path, root):
            continue
        text = load_file(path)
        if not text.strip():
            continue
        rel = path.relative_to(root)
        docs.append({
            "source": rel.as_posix(),
            # first folder name (e.g. "system-design-primer"), or "notes" for top-level files
            "topic": rel.parts[0] if len(rel.parts) > 1 else "notes",
            "suffix": path.suffix.lower(),
            "text": text,
        })
    return docs


def chunk_text(text, size=1000, overlap=150):
    """Fallback: cut long text into overlapping pieces."""
    chunks = []
    start = 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def split_numbered(text):
    """Split on headings like '1.2 Process vs thread' (the study guide PDF)."""
    text = HEADER_NOISE.sub("", text)
    matches = list(NUMBERED_HEADING.finditer(text))
    if not matches:                       # plain text with no recognisable headings
        return [("", text.strip())]

    sections = []
    intro = text[:matches[0].start()].strip()
    if intro:
        sections.append(("Introduction", intro))
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end].strip()
        if body:
            sections.append((m.group(0).strip(), body))
    return sections


def split_markdown(text):
    """Split on # headings. The heading path (Title > Section > Subsection)
    becomes the section name, so each chunk knows where it lives."""
    title = None
    fm = FRONTMATTER.match(text)
    if fm:
        t = re.search(r"^title:\s*(.+)$", fm.group(1), re.MULTILINE)
        if t:
            title = t.group(1).strip().strip("'\"")
        text = text[fm.end():]

    text = re.sub(r"<head>.*?</head>", "", text, flags=re.DOTALL)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = IMPORT_LINE.sub("", text)
    text = IMAGE.sub("", text)
    text = HTML_TAGS.sub("", text)

    sections = []
    stack = [(0, title)] if title else []      # (level, heading)
    body = []
    in_code = False

    def flush():
        content = "\n".join(body).strip()
        if content:
            sections.append((" > ".join(h for _, h in stack), content))
        body.clear()

    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_code = not in_code
        m = MD_HEADING.match(line)
        if m and not in_code:                  # '#' inside code blocks is just a comment
            flush()
            level = len(m.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, m.group(2).strip()))
        else:
            body.append(line)
    flush()
    return sections


def chunk_document(doc, max_chars=1200, min_chars=120):
    """One chunk per section; very long sections are split further.
    The heading is added to the chunk text so the embedding knows the topic."""
    if doc["suffix"] in (".md", ".mdx"):
        sections = split_markdown(doc["text"])
    else:
        sections = split_numbered(doc["text"])

    chunks = []
    for heading, body in sections:
        if heading and LINK_SECTION.search(heading.split(" > ")[-1]):
            continue                          # skips "Source(s) and further reading" link lists
        pieces = [body] if len(body) <= max_chars else chunk_text(body)
        for piece in pieces:
            if len(piece) < min_chars:        # skips tiny leftovers
                continue
            text = f"{heading}\n{piece}" if heading else piece
            chunks.append({
                "id": f"{doc['source']}-{len(chunks)}",
                "source": doc["source"],
                "topic": doc["topic"],
                "section": heading,
                "text": text,
            })
    return chunks


if __name__ == "__main__":
    docs = load_notes("notes")
    all_chunks = []
    for doc in docs:
        all_chunks.extend(chunk_document(doc))

    print(f"{len(docs)} files -> {len(all_chunks)} chunks\n")
    by_topic = {}
    for c in all_chunks:
        by_topic[c["topic"]] = by_topic.get(c["topic"], 0) + 1
    for topic, n in by_topic.items():
        print(f"  {topic}: {n} chunks")
