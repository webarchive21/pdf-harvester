import os
import hashlib
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

INDEX_PAGES = [
    "https://www.ayellet.org.il/our-magazine/"
    "https://toratchabad.com/%D7%92%D7%99%D7%9C%D7%99%D7%95%D7%A0%D7%95%D7%AA-%D7%90%D7%95%D7%A8-%D7%95%D7%97%D7%99%D7%95%D7%AA/"
]

OUT_DIR = "harvested_pdfs"
HASH_FILE = os.path.join(OUT_DIR, "hashes.txt")

os.makedirs(OUT_DIR, exist_ok=True)

existing_hashes = set()
if os.path.exists(HASH_FILE):
    with open(HASH_FILE, "r", encoding="utf-8") as f:
        existing_hashes = set(line.strip() for line in f)

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

new_files = 0

for page in INDEX_PAGES:
    print("Scanning:", page)
    pdf_links = get_pdf_links(page)

    for pdf_url in pdf_links:
        try:
            r = requests.get(pdf_url, timeout=30)
            if r.ok and "pdf" in r.headers.get("content-type", "").lower():
                h = sha256(r.content)
                if h not in existing_hashes:
                    filename = pdf_url.split("/")[-1]
                    path = os.path.join(OUT_DIR, filename)

                    with open(path, "wb") as f:
                        f.write(r.content)

                    with open(HASH_FILE, "a", encoding="utf-8") as f:
                        f.write(h + "\n")

                    existing_hashes.add(h)
                    new_files += 1
                    print("Downloaded:", filename)
                else:
                    print("Already exists:", pdf_url)
            else:
                print("Skipped (not PDF):", pdf_url)
        except Exception as e:
            print("Error:", pdf_url, e)

print(f"Finished. New PDFs: {new_files}")
