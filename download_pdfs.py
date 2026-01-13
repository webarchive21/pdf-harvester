import os
import re
import hashlib
import requests
import pdfplumber
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# ========= הגדרות =========

INDEX_PAGES = [
    "https://example.com/publications/"  # החלף לכתובת אמיתית
]

OUT_DIR = "harvested_pdfs"
HASH_FILE = os.path.join(OUT_DIR, "hashes.txt")

HEBREW_MONTHS = [
    "תשרי","חשוון","כסלו","טבת","שבט","אדר",
    "ניסן","אייר","סיוון","תמוז","אב","אלול"
]

MAGAZINE_NAME = "אדם_ועבודה"  # שנה אם צריך

# ==========================

os.makedirs(OUT_DIR, exist_ok=True)

existing_hashes = set()
if os.path.exists(HASH_FILE):
    with open(HASH_FILE, "r", encoding="utf-8") as f:
        existing_hashes = set(line.strip() for line in f)

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def safe_filename(text):
    text = re.sub(r"[^\w\u0590-\u05FF ]+", "", text)
    return re.sub(r"\s+", "_", text.strip())

def extract_issue_and_hebrew_date(pdf_path):
    """מחלץ מספר גיליון + חודש + שנה עברית מעמוד ראשון"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = pdf.pages[0].extract_text() or ""
    except Exception:
        return None, None, None

    issue = None
    month = None
    year = None

    issue_match = re.search(r"גליון\s*מס'?\s*(\d+)", text)
    if issue_match:
        issue = issue_match.group(1)

    for m in HEBREW_MONTHS:
        if m in text:
            month = m
            break

    year_match = re.search(r"תש[א-ת]{1,3}", text)
    if year_match:
        year = year_match.group(0)

    return issue, month, year

def get_pdf_links(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            links.add(urljoin(url, href))

    return sorted(links)

# ========= קציר =========

new_files = 0

for page in INDEX_PAGES:
    print("Scanning:", page)
    pdf_links = get_pdf_links(page)

    for pdf_url in pdf_links:
        try:
            r = requests.get(pdf_url, timeout=30)
            if not (r.ok and "pdf" in r.headers.get("content-type", "").lower()):
                print("Skipped (not PDF):", pdf_url)
                continue

            h = sha256(r.content)
            if h in existing_hashes:
                print("Already exists:", pdf_url)
                continue

            # שמירה זמנית
            temp_path = os.path.join(OUT_DIR, "temp.pdf")
            with open(temp_path, "wb") as f:
                f.write(r.content)

            issue, month, year = extract_issue_and_hebrew_date(temp_path)

            if issue and month and year:
                filename = f"{MAGAZINE_NAME}_גיליון_{issue}_{month}_{year}.pdf"
            else:
                filename = safe_filename(pdf_url.split("/")[-1])
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"

            final_path = os.path.join(OUT_DIR, filename)
            os.rename(temp_path, final_path)

            with open(HASH_FILE, "a", encoding="utf-8") as f:
                f.write(h + "\n")

            existing_hashes.add(h)
            new_files += 1
            print("Downloaded:", filename)

        except Exception as e:
            print("Error:", pdf_url, e)

print(f"Finished. New PDFs: {new_files}")
