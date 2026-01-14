import os
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import pdfplumber
import re

# ========================
# CONFIG
# ========================

INDEX_PAGES = [
    "https://www.ayellet.org.il/our-magazine/"
]

OUT_DIR = "harvested_pdfs"
HASH_FILE = os.path.join(OUT_DIR, "hashes.txt")

os.makedirs(OUT_DIR, exist_ok=True)

# ========================
# LOAD EXISTING HASHES
# ========================

existing_hashes = set()
if os.path.exists(HASH_FILE):
    with open(HASH_FILE, "r", encoding="utf-8") as f:
        existing_hashes = set(line.strip() for line in f)

# ========================
# HELPERS
# ========================

def sha256(data):
    return hashlib.sha256(data).hexdigest()

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

def extract_metadata_from_pdf(path):
    title = "publication"
    issue = "unknown"
    hebrew_date = "no-date"

    try:
        with pdfplumber.open(path) as pdf:
            text = pdf.pages[0].extract_text() or ""

        # מספר גיליון
        m_issue = re.search(r"גיליון\s*(\d+)", text)
        if m_issue:
            issue = m_issue.group(1)

        # תאריך עברי (פשוט)
        m_date = re.search(
            r"(תשרי|חשוון|כסלו|טבת|שבט|אדר|ניסן|אייר|סיוון|תמוז|אב|אלול)\s+תשפ״?\w",
            text
        )
        if m_date:
            hebrew_date = m_date.group(0).replace(" ", "_")

        # שם פרסום
        if "איילת" in text:
            title = "איילת_השחר"

    except Exception as e:
        print("Metadata error:", e)

    return title, issue, hebrew_date

# ========================
# MAIN
# ========================

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

            # חילוץ metadata + naming
            title, issue, hebrew_date = extract_metadata_from_pdf(temp_path)
            filename = f"{title}_{hebrew_date}_גיליון_{issue}.pdf"
            final_path = os.path.join(OUT_DIR, filename)

            os.rename(temp_path, final_path)

            # שמירת hash
            with open(HASH_FILE, "a", encoding="utf-8") as f:
                f.write(h + "\n")

            existing_hashes.add(h)
            new_files += 1
            print("Downloaded:", filename)

        except Exception as e:
            print("Error:", pdf_url, e)

print(f"Finished. New PDFs: {new_files}")
