import pandas as pd
import requests, os, time, re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

EMAIL = "iamthebestguy786@gmail.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, Gecko) Chrome/137.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
}
SCIHUB_MIRRORS = ["https://sci-hub.ru", "https://sci-hub.st", "https://sci-hub.red", "https://sci-hub.su"]

def get_biorxiv_pdf(doi):
    return f"https://www.biorxiv.org/content/{doi}.full.pdf"

def get_scihub_pdf(doi):
    for mirror in SCIHUB_MIRRORS:
        try:
            r = requests.get(f"{mirror}/{doi}", headers=HEADERS, timeout=20)
            if r.status_code == 200:
                soup = BeautifulSoup(r.content, "html.parser")
                iframe = soup.find("iframe", id="pdf")
                if iframe and iframe.get("src"):
                    p = iframe["src"]
                    if p.startswith("//"): p = "https:" + p
                    elif not p.startswith("http"): p = mirror + p
                    return p
        except: continue
    return None

def download_file(url, folder, filename):
    try:
        os.makedirs(folder, exist_ok=True)
        r = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
        if r.status_code == 200 and ("pdf" in r.headers.get("Content-Type", "").lower() or url.lower().endswith(".pdf")):
            with open(filename, "wb") as f: f.write(r.content)
            return True
    except: pass
    return False

def download_with_selenium(url, folder, doi):
    try:
        options = webdriver.ChromeOptions()
        prefs = {"download.default_directory": os.path.abspath(folder), "plugins.always_open_pdf_externally": True}
        options.add_experimental_option("prefs", prefs)
        options.add_argument("--headless")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url); time.sleep(15); driver.quit(); return True
    except: return False

def main():
    papers = pd.read_csv("papers_master.csv")
    downloaded = 0; failed_list = []
    print("\nULTIMATE PDF DOWNLOADER V3\n" + "="*40)
    for _, row in papers.iterrows():
        doi, folder = str(row["doi"]).strip(), str(row["folder"]).strip()
        filename = os.path.join(folder, doi.replace("/", "_") + ".pdf")
        if os.path.exists(filename):
            print(f"[SKIPPED] {doi}"); downloaded += 1; continue
        print(f"[PROCESSING] {doi}")
        u, s = None, "None"
        if "arxiv" in doi.lower():
            u = f"https://arxiv.org/pdf/{doi.split('arXiv.')[-1] if 'arXiv.' in doi else doi.split('/')[-1]}.pdf"; s = "arXiv"
        elif "10.1101/" in doi: u = get_biorxiv_pdf(doi); s = "bioRxiv"
        elif "10.26434/chemrxiv" in doi: u = f"https://chemrxiv.org/engage/api-gateway/chemrxiv/assets/orp/resource/item/{doi.split('.')[-1]}/original/pdf"; s = "ChemRxiv"
        if not u:
            try:
                r = requests.get(f"https://api.crossref.org/works/{doi}", timeout=15)
                if r.status_code == 200:
                    for l in r.json()["message"].get("link", []):
                        if "pdf" in l.get("content-type", "").lower(): u = l["URL"]; s = "CrossRef"; break
            except: pass
        if not u:
            try:
                r = requests.get(f"https://api.unpaywall.org/v2/{doi}?email={EMAIL}", timeout=15)
                if r.status_code == 200: u = r.json().get("best_oa_location", {}).get("url_for_pdf"); s = "Unpaywall"
            except: pass
        if not u: print("  Searching Sci-Hub..."); u = get_scihub_pdf(doi); s = "Sci-Hub"
        ok = download_file(u, folder, filename) if u else False
        if not ok: print("  Trying Selenium..."); ok = download_with_selenium(f"https://doi.org/{doi}", folder, doi)
        if ok: print(f"  SUCCESS ({s})"); downloaded += 1
        else: print("  FAILED"); failed_list.append({"doi": doi, "folder": folder})
        time.sleep(2)
    if failed_list: pd.DataFrame(failed_list).to_csv("manual_review.csv", index=False)
    print(f"\nDONE. Downloaded: {downloaded}, Failed: {len(failed_list)}")

if __name__ == "__main__": main()
