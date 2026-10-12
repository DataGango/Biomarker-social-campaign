from html.parser import HTMLParser
from pathlib import Path

import requests
from pypdf import PdfReader

PDF_URL = (
    "https://www.cancer.org/content/dam/cancer-org/"
    "cancer-control/en/booklets-flyers/cancer-biomarkers.pdf"
)

PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"
PDF_PATH = DATA_DIR / "cancer_biomarkers.pdf"
WEB_URL = "https://www.cancer.org/cancer/types/leukemia-in-children/detection-diagnosis-staging/survival-rates.html"
WEB_TEXT_PATH = DATA_DIR / "leukemia_survival_rates.txt"
GENETICS_URL = "https://www.cancer.org/cancer/risk-prevention/genetics.html"
GENETICS_TEXT_PATH = DATA_DIR / "cancer_genetics.txt"
CHEMICALS_URL = "https://www.cancer.org/cancer/risk-prevention/chemicals.html"
CHEMICALS_TEXT_PATH = DATA_DIR / "cancer_chemicals.txt"
EARLY_DETECTION_URL = "https://www.cancer.org/research/early-detection-team.html"
EARLY_DETECTION_TEXT_PATH = DATA_DIR / "acs_early_detection_team.txt"
CHILDHOOD_CANCER_URL = "https://www.cancer.gov/types/childhood-cancers/child-adolescent-cancers-fact-sheet"
CHILDHOOD_CANCER_TEXT_PATH = DATA_DIR / "childhood_cancer_nci.txt"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
WEB_SOURCES = [
    ("CHILDHOOD LEUKEMIA SURVIVAL RATES", WEB_URL, WEB_TEXT_PATH),
    ("CANCER GENETICS", GENETICS_URL, GENETICS_TEXT_PATH),
    ("CHEMICALS AND CANCER RISK", CHEMICALS_URL, CHEMICALS_TEXT_PATH),
    ("ACS EARLY DETECTION TEAM", EARLY_DETECTION_URL, EARLY_DETECTION_TEXT_PATH),
    ("CHILDHOOD CANCER: NCI FACT SHEET", CHILDHOOD_CANCER_URL, CHILDHOOD_CANCER_TEXT_PATH),
]


def _atomic_write(path, content, *, binary=False):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(path.name + ".tmp")
    try:
        if binary:
            temporary_path.write_bytes(content)
        else:
            temporary_path.write_text(content, encoding="utf-8")
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


class PageTextParser(HTMLParser):
    """Collect readable page text while ignoring non-content elements."""

    BLOCK_TAGS = {"article", "br", "div", "h1", "h2", "h3", "li", "p", "section", "tr"}
    IGNORED_TAGS = {"footer", "nav", "script", "style", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.IGNORED_TAGS:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.IGNORED_TAGS and self.ignored_depth:
            self.ignored_depth -= 1
        elif not self.ignored_depth and tag in self.BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored_depth:
            text = " ".join(data.split())
            if text:
                self.parts.append(text)

    def get_text(self):
        return "\n".join(line.strip() for line in " ".join(self.parts).splitlines() if line.strip())


def download_pdf():
    response = requests.get(PDF_URL, timeout=30)
    response.raise_for_status()
    if not response.content.startswith(b"%PDF"):
        raise ValueError(f"Downloaded content from {PDF_URL} is not a PDF")
    _atomic_write(PDF_PATH, response.content, binary=True)

    print(f"Downloaded: {PDF_PATH}")


def extract_text():

    reader = PdfReader(PDF_PATH)

    pages = []

    for page_number, page in enumerate(reader.pages):

        text = page.extract_text()

        pages.append({
            "page": page_number + 1,
            "text": text
        })

    return pages


def ingest_webpage(url=WEB_URL, text_path=WEB_TEXT_PATH):
    response = requests.get(url, timeout=30, headers=REQUEST_HEADERS)
    response.raise_for_status()

    parser = PageTextParser()
    parser.feed(response.text)
    text = parser.get_text()
    if not text:
        raise ValueError(f"No readable text found at {url}")

    target_path = Path(text_path)
    if not target_path.is_absolute():
        target_path = PROJECT_DIR / target_path
    _atomic_write(target_path, f"Source: {url}\n\n{text}\n")

    print(f"Extracted webpage text: {text_path}")
    return text


def refresh_sources():
    """Scrape all configured web sources and report each source outcome."""
    sources = [("ACS biomarker fact sheet PDF", PDF_URL, PDF_PATH, download_pdf)]
    sources.extend(
        (title, url, path, lambda url=url, path=path: ingest_webpage(url, path))
        for title, url, path in WEB_SOURCES
    )
    outcomes = []
    for title, url, path, fetch in sources:
        try:
            fetch()
            outcomes.append({"title": title, "url": url, "path": str(path), "ok": True, "error": None})
        except (requests.RequestException, OSError, ValueError) as error:
            outcomes.append({"title": title, "url": url, "path": str(path), "ok": False, "error": str(error)})
    return outcomes


if __name__ == "__main__":

    download_pdf()

    pages = extract_text()

    for page in pages:
        print("=" * 80)
        print(f"PAGE {page['page']}")
        print("=" * 80)
        print(page["text"])

    web_sources = [
        ("CHILDHOOD LEUKEMIA SURVIVAL RATES", WEB_URL, WEB_TEXT_PATH),
        ("CANCER GENETICS", GENETICS_URL, GENETICS_TEXT_PATH),
        ("CHEMICALS AND CANCER RISK", CHEMICALS_URL, CHEMICALS_TEXT_PATH),
        ("ACS EARLY DETECTION TEAM", EARLY_DETECTION_URL, EARLY_DETECTION_TEXT_PATH),
        ("CHILDHOOD CANCER: NCI FACT SHEET", CHILDHOOD_CANCER_URL, CHILDHOOD_CANCER_TEXT_PATH),
    ]
    for title, url, text_path in web_sources:
        print("=" * 80)
        print(title)
        print("=" * 80)
        try:
            print(ingest_webpage(url, text_path))
        except (requests.RequestException, ValueError) as error:
            print(f"Could not ingest {url}: {error}")
