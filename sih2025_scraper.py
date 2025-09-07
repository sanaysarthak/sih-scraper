import re
import json
import argparse
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup, Tag
import pandas as pd

URL = "https://www.sih.gov.in/sih2025PS"

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
    ps_code: Optional[str] = None
    ideas_count: Optional[str] = None
    list_category: Optional[str] = None
    list_theme: Optional[str] = None

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
    return re.sub(r"[ \t]+", " ", elem.get_text("\n", strip=True)).strip()

def extract_blocks(soup: BeautifulSoup) -> List[Tag]:
    blocks = []
    for tag in soup.find_all(text=re.compile(r"Problem Statement Details", re.I)):
        c = tag
        for _ in range(5):
            if isinstance(c, Tag) and c.parent:
                c = c.parent
        if isinstance(c, Tag):
            blocks.append(c)
    uniq, seen = [], set()
    for b in blocks:
        k = id(b)
        if k not in seen:
            uniq.append(b)
            seen.add(k)
    return uniq

def split_into_labeled_chunks(block_text: str) -> Dict[str, str]:
    lines = [l.strip() for l in block_text.split("\n") if l.strip()]
    text = "\n".join(lines)

    data, positions = {}, []
    for key in DETAIL_KEYS:
        m = re.search(rf"(?m)^{re.escape(key)}\s*$", text, flags=re.IGNORECASE)
        if m:
            positions.append((key, m.start()))
    positions.sort(key=lambda x: x[1])
    if not positions:
        return data
    positions.append(("__END__", len(text)))

    for i in range(len(positions) - 1):
        key, start = positions[i]
        _, nxt = positions[i + 1]
        end_line = text.find("\n", start)
        if end_line == -1:
            end_line = start
        value = text[end_line:nxt].strip()
        value = re.sub(r"\n•\s*", "\n• ", value)
        data[key] = value.strip()
    return data

def parse_footer_line(block_text: str) -> Dict[str, str]:
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
    raw = cleaned_text(block)
    labeled = split_into_labeled_chunks(raw)
    footer = parse_footer_line(raw)

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
    if not rec.category and rec.list_category:
        rec.category = rec.list_category
    if not rec.theme and rec.list_theme:
        rec.theme = rec.list_theme
    return rec

def scrape_sih_ps(url: str) -> List[ProblemStatement]:
    html = fetch_html(url)
    soup = BeautifulSoup(html, "lxml")
    blocks = extract_blocks(soup)

    if not blocks:
        full = cleaned_text(soup.body or soup)
        parts = re.split(r"(?i)\bProblem Statement Details\b", full)
        blocks = []
        for p in parts[1:]:
            class Dummy(Tag):
                def __init__(self, text): self._text = text
                def get_text(self, *a, **k): return self._text
            blocks.append(Dummy("Problem Statement Details\n" + p))

    recs = []
    for b in blocks:
        try:
            r = make_record(b)
            if any(getattr(r, f) for f in asdict(r)):
                recs.append(r)
        except Exception:
            continue

    seen, uniq = set(), []
    for r in recs:
        k = (r.problem_statement_id or "").strip() or (r.ps_code or "").strip()
        if not k:
            k = f"UNK-{len(uniq)}"
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    return uniq

def export(records: List[ProblemStatement], out_base: str, formats: List[str]) -> None:
    rows = [asdict(r) for r in records]
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
    parser.add_argument("--url", default=URL)
    parser.add_argument("--out-base", default="sih2025_problem_statements")
    parser.add_argument("--formats", nargs="+", default=["csv", "json", "xlsx"])
    args = parser.parse_args()

    print(f"Fetching: {args.url}")
    recs = scrape_sih_ps(args.url)
    print(f"Found {len(recs)} problem statements.")

    export(recs, args.out_base, [f.lower() for f in args.formats])
    print(
        "Exported to: "
        + ", ".join(
            f"{args.out_base}.{('xlsx' if ext.lower() == 'excel' else ext.lower())}"
            for ext in args.formats
        )
    )

if __name__ == "__main__":
    main()
