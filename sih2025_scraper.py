import re
import json
import argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup, Tag
import pandas as pd

URL = "https://www.sih.gov.in/sih2025PS"

# Keys we try to extract from each "Problem Statement Details" block.
DETAIL_KEYS = [
    "Problem Statement ID",
    "Problem Statement Title",
    "Description",
    "Background",
    "Expected Solution",
    "Organization",
    "Department",
    "Category",
    "Theme",
    "Youtube Link",
    "Dataset Link",
    "Contact info",
]

# Some pages include a footer line like:
#   "Software SIH25001 0 MedTech / BioTech / HealthTech"
# We parse this as {Category, PS Code, Ideas Count (if present), Theme (again)}
PS_CODE_LINE_RE = re.compile(
    r"(?P<category>Software|Hardware)\s+(?P<ps_code>SIH\d{5})\s+(?P<ideas>\d+)?\s*(?P<theme>.*)?",
    re.IGNORECASE,
)

@dataclass
class ProblemStatement:
    problem_statement_id: Optional[str] = None
    problem_statement_title: Optional[str] = None
    description: Optional[str] = None
    background: Optional[str] = None
    expected_solution: Optional[str] = None
    organization: Optional[str] = None
    department: Optional[str] = None
    category: Optional[str] = None
    theme: Optional[str] = None
    youtube_link: Optional[str] = None
    dataset_link: Optional[str] = None
    contact_info: Optional[str] = None
    ps_code: Optional[str] = None           # e.g., SIH25001
    ideas_count: Optional[str] = None       # from footer line (if present)
    list_category: Optional[str] = None     # category inferred from footer line
    list_theme: Optional[str] = None        # theme inferred from footer line

def fetch_html(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.text

def cleaned_text(elem: Tag) -> str:
    # Collapse spaces/newlines nicely
    return re.sub(r"[ \t]+", " ", elem.get_text("\n", strip=True)).strip()

def is_details_header(node: Tag) -> bool:
    # The details blocks on the page have a small header like "Problem Statement Details"
    if not isinstance(node, Tag):
        return False
    txt = node.get_text(strip=True).lower()
    return "problem statement details" in txt

def extract_blocks(soup: BeautifulSoup) -> List[Tag]:
    # Strategy: find all small headers containing "Problem Statement Details"
    # and use their nearest parent/container to parse.
    candidates = []
    for tag in soup.find_all(text=re.compile(r"Problem Statement Details", re.I)):
        # Usually this text is inside a header (e.g., h6) or a label
        container = tag
        # Climb up a bit to get the full block
        for _ in range(5):
            if isinstance(container, Tag) and container.parent:
                container = container.parent
        if isinstance(container, Tag):
            candidates.append(container)
    # Deduplicate by element id
    uniq = []
    seen = set()
    for c in candidates:
        key = id(c)
        if key not in seen:
            uniq.append(c)
            seen.add(key)
    return uniq

def split_into_labeled_chunks(block_text: str) -> Dict[str, str]:
    """
    The block has repeating pattern:
      Problem Statement ID
      25001
      Problem Statement Title
      Title text...
      Description
      ...
    We split by our known labels and capture the text in between.
    """
    # Normalize line endings
    lines = [l.strip() for l in block_text.split("\n") if l.strip()]

    # Build a compact string with \n to keep structure but avoid excess blanks
    text = "\n".join(lines)

    # Build a pattern that finds each key as a heading; capture text until next key or end
    # We'll iterate progressively.
    data: Dict[str, str] = {}
    # Create positions of each key in the text
    # To make robust, we allow for minor punctuation/spaces differences
    key_positions = []
    for key in DETAIL_KEYS:
        m = re.search(rf"(?m)^{re.escape(key)}\s*$", text, flags=re.IGNORECASE)
        if m:
            key_positions.append((key, m.start()))
    key_positions.sort(key=lambda x: x[1])

    # If no labeled keys were found, return empty
    if not key_positions:
        return data

    # Add end sentinel
    key_positions.append(("__END__", len(text)))

    # Slice chunks
    for i in range(len(key_positions) - 1):
        key, start = key_positions[i]
        _, next_start = key_positions[i + 1]
        # Value starts after the line containing the key
        # Find end of that line
        end_of_key_line = text.find("\n", start)
        if end_of_key_line == -1:
            end_of_key_line = start
        value = text[end_of_key_line:next_start].strip()
        # Clean bullets spacing a bit
        value = re.sub(r"\n•\s*", "\n• ", value)
        # Remove accidental repeated labels within value
        data[key] = value.strip(" \n\r\t")
    return data

def parse_footer_line(block_text: str) -> Dict[str, str]:
    """
    Looks for a line like:
    'Software SIH25001 0 MedTech / BioTech / HealthTech'
    and returns parsed items.
    """
    # Look for a line that starts with Software/Hardware and contains SIHxxxxx
    for line in block_text.split("\n"):
        line = line.strip()
        m = PS_CODE_LINE_RE.match(line)
        if m:
            d = m.groupdict()
            return {
                "list_category": (d.get("category") or "").strip(),
                "ps_code": (d.get("ps_code") or "").strip(),
                "ideas_count": (d.get("ideas") or "").strip(),
                "list_theme": (d.get("theme") or "").strip(),
            }
    return {}

def make_record(block: Tag) -> ProblemStatement:
    raw_text = cleaned_text(block)

    labeled = split_into_labeled_chunks(raw_text)
    footer = parse_footer_line(raw_text)

    rec = ProblemStatement(
        problem_statement_id=labeled.get("Problem Statement ID"),
        problem_statement_title=labeled.get("Problem Statement Title"),
        description=labeled.get("Description"),
        background=labeled.get("Background"),
        expected_solution=labeled.get("Expected Solution"),
        organization=labeled.get("Organization"),
        department=labeled.get("Department"),
        category=labeled.get("Category"),
        theme=labeled.get("Theme"),
        youtube_link=labeled.get("Youtube Link"),
        dataset_link=labeled.get("Dataset Link"),
        contact_info=labeled.get("Contact info"),
        ps_code=footer.get("ps_code"),
        ideas_count=footer.get("ideas_count"),
        list_category=footer.get("list_category"),
        list_theme=footer.get("list_theme"),
    )
    # If top-level Category/Theme is missing, fill from footer inference
    if not rec.category and rec.list_category:
        rec.category = rec.list_category
    if not rec.theme and rec.list_theme:
        rec.theme = rec.list_theme
    return rec

def scrape_sih_ps(url: str) -> List[ProblemStatement]:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")

    # Extract all details blocks
    blocks = extract_blocks(soup)
    # If we failed to find blocks (structure changed), fall back:
    if not blocks:
        # Fallback: try to split the full page text on the heading marker
        full = cleaned_text(soup.body or soup)
        parts = re.split(r"(?i)\bProblem Statement Details\b", full)
        blocks = []
        for p in parts[1:]:
            # Wrap in a dummy tag-like object with text in .get_text()
            class Dummy(Tag):
                def __init__(self, text):
                    self._text = text
                def get_text(self, *args, **kwargs):
                    return self._text
            blocks.append(Dummy("Problem Statement Details\n" + p))

    records = []
    for b in blocks:
        try:
            rec = make_record(b)
            # Skip completely empty (rare)
            if any(getattr(rec, f) for f in asdict(rec)):
                records.append(rec)
        except Exception:
            # Be tolerant; continue others
            continue

    # Deduplicate by (problem_statement_id or ps_code)
    seen_keys = set()
    unique_records = []
    for r in records:
        key = (r.problem_statement_id or "").strip() or (r.ps_code or "").strip()
        if not key:
            # if neither present, include but mark with incremental key
            key = f"UNK-{len(unique_records)}"
        if key not in seen_keys:
            seen_keys.add(key)
            unique_records.append(r)

    return unique_records

def export(records: List[ProblemStatement], out_base: str, formats: List[str]) -> None:
    rows: List[Dict[str, Any]] = [asdict(r) for r in records]
    df = pd.DataFrame(rows)

    if "csv" in formats:
        df.to_csv(f"{out_base}.csv", index=False, encoding="utf-8-sig")
    if "json" in formats:
        with open(f"{out_base}.json", "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=2)
    if "xlsx" in formats or "excel" in formats:
        df.to_excel(f"{out_base}.xlsx", index=False)

def main():
    parser = argparse.ArgumentParser(description="Scrape SIH 2025 Problem Statements and export to CSV/JSON/Excel.")
    parser.add_argument("--url", default=URL, help="SIH 2025 PS URL (default: official page).")
    parser.add_argument("--out-base", default="sih2025_problem_statements", help="Output file base name (no extension).")
    parser.add_argument("--formats", nargs="+", default=["csv", "json", "xlsx"],
                        help="Any of: csv json xlsx (or excel)")

    args = parser.parse_args()

    print(f"Fetching: {args.url}")
    records = scrape_sih_ps(args.url)
    print(f"Found {len(records)} problem statements.")

    export(records, args.out_base, [f.lower() for f in args.formats])

    print(
        "Exported to: "
        + ", ".join(
            f"{args.out_base}.{('xlsx' if ext.lower() == 'excel' else ext.lower())}"
            for ext in args.formats
        )
    )

if __name__ == "__main__":
    main()
