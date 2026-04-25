"""
Apple Quarterly Earnings Downloader — FIXED & VERIFIED
========================================================
Downloads all Apple quarterly earnings press releases (FY2020-FY2025+)
directly from SEC EDGAR and saves them as HTML files in the data/ folder.
HTML files can then be printed to PDF via Chrome (Ctrl+P > Save as PDF).

Usage:
    pip install requests
    python download_apple_earnings.py

All URLs verified directly from SEC EDGAR index pages.
"""

import os
import time
import requests

BASE = "https://www.sec.gov/Archives/edgar/data/320193"

# ─────────────────────────────────────────────────────────────
# ALL URLS VERIFIED DIRECTLY FROM SEC EDGAR INDEX PAGES
# ─────────────────────────────────────────────────────────────

EARNINGS = [

    # ── FY2026 Q1 (bonus — most recent, Jan 2026) ─────────────
    {"name": "apple_fy2026_q1.htm", "label": "FY2026 Q1 | Dec 2025 | $143.8B | Jan 29 2026",
     "url": f"{BASE}/000032019326000005/a8-kex991q1202612272025.htm"},

    # ── FY2025 ────────────────────────────────────────────────
    {"name": "apple_fy2025_q4.htm", "label": "FY2025 Q4 | Sep 2025 | $102.5B | Oct 30 2025",
     "url": f"{BASE}/000032019325000077/a8-kex991q4202509272025.htm"},
    {"name": "apple_fy2025_q3.htm", "label": "FY2025 Q3 | Jun 2025 | $94.0B  | Jul 31 2025",
     "url": f"{BASE}/000032019325000071/a8-kex991q3202506282025.htm"},
    {"name": "apple_fy2025_q2.htm", "label": "FY2025 Q2 | Mar 2025 | $95.4B  | May 01 2025",
     "url": f"{BASE}/000032019325000055/a8-kex991q2202503292025.htm"},
    {"name": "apple_fy2025_q1.htm", "label": "FY2025 Q1 | Dec 2024 | $124.3B | Jan 30 2025",
     "url": f"{BASE}/000032019325000007/a8-kex991q1202512282024.htm"},

    # ── FY2024 ────────────────────────────────────────────────
    {"name": "apple_fy2024_q4.htm", "label": "FY2024 Q4 | Sep 2024 | $94.9B  | Oct 31 2024",
     "url": f"{BASE}/000032019324000120/a8-kex991q4202409282024.htm"},
    {"name": "apple_fy2024_q3.htm", "label": "FY2024 Q3 | Jun 2024 | $85.8B  | Aug 01 2024",
     "url": f"{BASE}/000032019324000081/a8-kex991q3202406292024.htm"},
    {"name": "apple_fy2024_q2.htm", "label": "FY2024 Q2 | Mar 2024 | $90.8B  | May 02 2024",
     "url": f"{BASE}/000032019324000042/a8-kex991q2202403302024.htm"},
    {"name": "apple_fy2024_q1.htm", "label": "FY2024 Q1 | Dec 2023 | $119.6B | Feb 01 2024",
     "url": f"{BASE}/000032019324000008/a8-kex991q1202412302023.htm"},

    # ── FY2023 ────────────────────────────────────────────────
    {"name": "apple_fy2023_q4.htm", "label": "FY2023 Q4 | Sep 2023 | $89.5B  | Nov 02 2023",
     "url": f"{BASE}/000032019323000104/a8-kex991q4202309302023.htm"},
    {"name": "apple_fy2023_q3.htm", "label": "FY2023 Q3 | Jul 2023 | $81.8B  | Aug 03 2023",
     "url": f"{BASE}/000032019323000077/a8-kex991q3202307012023.htm"},
    {"name": "apple_fy2023_q2.htm", "label": "FY2023 Q2 | Apr 2023 | $94.8B  | May 04 2023",
     "url": f"{BASE}/000032019323000044/a8-kex991q2202304012023.htm"},
    {"name": "apple_fy2023_q1.htm", "label": "FY2023 Q1 | Dec 2022 | $117.2B | Feb 02 2023",
     "url": f"{BASE}/000032019323000005/a8-kex991q1202312312022.htm"},

    # ── FY2022 ────────────────────────────────────────────────
    {"name": "apple_fy2022_q4.htm", "label": "FY2022 Q4 | Sep 2022 | $90.1B  | Oct 27 2022",
     "url": f"{BASE}/000032019322000107/a8-kex991q4202209242022.htm"},
    {"name": "apple_fy2022_q3.htm", "label": "FY2022 Q3 | Jun 2022 | $83.0B  | Jul 28 2022",
     "url": f"{BASE}/000032019322000069/a8-kex991q3202206252022.htm"},
    {"name": "apple_fy2022_q2.htm", "label": "FY2022 Q2 | Mar 2022 | $97.3B  | Apr 28 2022",
     "url": f"{BASE}/000032019322000043/a8-kex991q2202203262022.htm"},
    {"name": "apple_fy2022_q1.htm", "label": "FY2022 Q1 | Dec 2021 | $123.9B | Jan 27 2022",
     "url": f"{BASE}/000032019322000004/a8-kex991q1202212252021.htm"},

    # ── FY2021 ────────────────────────────────────────────────
    {"name": "apple_fy2021_q4.htm", "label": "FY2021 Q4 | Sep 2021 | $83.4B  | Oct 28 2021",
     "url": f"{BASE}/000032019321000104/a8-kex991q4202109252021.htm"},
    {"name": "apple_fy2021_q3.htm", "label": "FY2021 Q3 | Jun 2021 | $81.4B  | Jul 27 2021",
     "url": f"{BASE}/000032019321000063/a8-kex991q3202106262021.htm"},
    {"name": "apple_fy2021_q2.htm", "label": "FY2021 Q2 | Mar 2021 | $89.6B  | Apr 28 2021",
     "url": f"{BASE}/000032019321000055/a8-kex991q2202103272021.htm"},
    {"name": "apple_fy2021_q1.htm", "label": "FY2021 Q1 | Dec 2020 | $111.4B | Jan 27 2021",
     "url": f"{BASE}/000032019321000009/a8-kex991q1202112262020.htm"},

    # ── FY2020 ────────────────────────────────────────────────
    {"name": "apple_fy2020_q4.htm", "label": "FY2020 Q4 | Sep 2020 | $64.7B  | Oct 29 2020",
     "url": f"{BASE}/000032019320000094/a8-kex991q420209262020.htm"},
    {"name": "apple_fy2020_q3.htm", "label": "FY2020 Q3 | Jun 2020 | $59.7B  | Jul 30 2020",
     "url": f"{BASE}/000032019320000060/a8-kexhibit991q3202062.htm"},
    {"name": "apple_fy2020_q2.htm", "label": "FY2020 Q2 | Mar 2020 | $58.3B  | Apr 30 2020",
     "url": f"{BASE}/000032019320000050/a8-kexhibit991q2202032.htm"},
    {"name": "apple_fy2020_q1.htm", "label": "FY2020 Q1 | Dec 2019 | $91.8B  | Jan 28 2020",
     "url": f"{BASE}/000032019320000008/a8-kexhibit991q1202012.htm"},
]

HEADERS = {
    "User-Agent": "Research/1.0 dipukamruzzaman1@gmail.com",
    "Accept": "text/html,application/xhtml+xml",
}

OUTPUT_DIR = "data"


OUTPUT_DIR = "data"


def download_as_html(item, output_dir):
    url      = item["url"]
    filename = item["name"]
    label    = item.get("label", filename)
    filepath = os.path.join(output_dir, filename)

    if os.path.exists(filepath):
        print(f"  ⏭️  Already exists : {filename}")
        return True

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        if response.status_code == 200:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(response.text)
            size_kb = len(response.content) / 1024
            print(f"  ✅ {label}  ({size_kb:.0f} KB)")
            return True
        else:
            print(f"  ❌ Failed {response.status_code} : {label}")
            print(f"     {url}")
            return False
    except Exception as e:
        print(f"  ❌ Error : {label} — {e}")
        return False


def print_manual_pdf_instructions(output_dir):
    htm_files = sorted([f for f in os.listdir(output_dir) if f.endswith(".htm")])
    if not htm_files:
        return
    print(f"\n{'─'*60}")
    print(f"  📄 Convert {len(htm_files)} HTML files → PDF:")
    print(f"{'─'*60}")
    print("  1. Open each .htm file in Chrome")
    print("  2. Press Ctrl+P")
    print("  3. Change Destination to 'Save as PDF'")
    print("  4. Save with the same name but .pdf extension")
    print("  5. Delete the .htm file after saving")
    print(f"\n  Files to convert:")
    for f in htm_files:
        print(f"    → data/{f}")


def main():
    print("=" * 60)
    print("  Apple Earnings Downloader — VERIFIED URLS")
    print(f"  {len(EARNINGS)} quarters | FY2020–FY2026 | SEC EDGAR")
    print("=" * 60)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\n📁 Output folder: ./{OUTPUT_DIR}/\n")

    success, failed, failed_items = 0, 0, []

    for item in EARNINGS:
        result = download_as_html(item, OUTPUT_DIR)
        if result:
            success += 1
        else:
            failed += 1
            failed_items.append(item)
        time.sleep(0.4)

    print(f"\n{'='*60}")
    print(f"  ✅ Downloaded : {success} / {len(EARNINGS)}")
    if failed_items:
        print(f"  ❌ Failed     : {failed}")
        print(f"\n  Retry these manually:")
        for item in failed_items:
            print(f"    {item.get('label', item['name'])}")
            print(f"    {item['url']}")

    print_manual_pdf_instructions(OUTPUT_DIR)

    pdf_count = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".pdf")])
    htm_count = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".htm")])

    print(f"\n{'='*60}")
    print(f"  PDFs ready for RAG : {pdf_count}")
    print(f"  HTML (need PDF)    : {htm_count}")
    print(f"{'='*60}")
    print(f"\n  After converting all HTMLs to PDF run:")
    print(f"  python populate_database.py --reset")
    print(f"  python query_data.py \"What was Apple revenue in Q4 FY2024?\"\n")


if __name__ == "__main__":
    main()