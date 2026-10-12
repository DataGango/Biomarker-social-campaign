"""Render the cited childhood-cancer research brief as a linked PDF."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

import markdown


PROJECT_DIR = Path(__file__).resolve().parent
SOURCE_PATH = PROJECT_DIR / "childhood-cancer-site" / "childhood_cancer_research.md"
OUTPUT_PATH = PROJECT_DIR / "childhood-cancer-site" / "childhood_cancer_research.pdf"
CHROME_PATH = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


PRINT_STYLES = """
@page { size: Letter; margin: 0.72in 0.78in; }
:root { color-scheme: light; }
body { color: #202b28; font: 10.5pt/1.52 Georgia, 'Times New Roman', serif; }
main { max-width: 7in; margin: 0 auto; }
h1 { margin: 0 0 12pt; color: #173d34; font: 25pt/1.15 Georgia, 'Times New Roman', serif; }
h2 { margin: 22pt 0 8pt; padding-bottom: 4pt; border-bottom: 1px solid #cbd8d1; color: #17624f; font: 16pt/1.2 Georgia, 'Times New Roman', serif; break-after: avoid; }
h3 { margin: 16pt 0 6pt; font-size: 12pt; break-after: avoid; }
p { margin: 0 0 9pt; orphans: 3; widows: 3; }
strong { color: #173d34; }
a { color: #17624f; overflow-wrap: anywhere; }
li { margin: 0 0 7pt; }
blockquote { margin: 10pt 0; padding-left: 12pt; border-left: 3px solid #cf624b; }
code { font: 9pt Menlo, monospace; }
hr { border: 0; border-top: 1px solid #cbd8d1; }
"""


def main() -> Path:
    if not SOURCE_PATH.is_file():
        raise FileNotFoundError("Research paper not found: {}".format(SOURCE_PATH))
    chrome = shutil.which(str(CHROME_PATH))
    if not chrome:
        raise RuntimeError("Google Chrome is required for PDF export: {}".format(CHROME_PATH))

    body = markdown.markdown(
        SOURCE_PATH.read_text(encoding="utf-8"),
        extensions=["tables", "sane_lists", "smarty"],
        output_format="html5",
    )
    base_url = PROJECT_DIR.as_uri() + "/"
    document = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><base href="{base}">
<title>Childhood Cancer Research Brief</title><style>{styles}</style></head>
<body><main>{body}</main></body></html>""".format(base=base_url, styles=PRINT_STYLES, body=body)

    with tempfile.TemporaryDirectory(prefix="childhood-cancer-pdf-") as temp_dir:
        html_path = Path(temp_dir) / "research.html"
        profile_path = Path(temp_dir) / "chrome-profile"
        html_path.write_text(document, encoding="utf-8")
        command = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--disable-extensions",
            "--no-pdf-header-footer",
            "--user-data-dir={}".format(profile_path),
            "--print-to-pdf={}".format(OUTPUT_PATH),
            html_path.as_uri(),
        ]
        try:
            process = subprocess.run(command, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            process = None
        if not OUTPUT_PATH.is_file():
            detail = "Chrome did not finish writing the PDF."
            if process is not None:
                detail = (process.stderr or process.stdout).strip() or detail
            raise RuntimeError("Chrome PDF export failed: {}".format(detail))
        from pypdf import PdfReader

        rendered_text = "\n".join(page.extract_text() or "" for page in PdfReader(str(OUTPUT_PATH)).pages)
        if "Childhood Cancer" not in rendered_text or "Limitations" not in rendered_text:
            raise RuntimeError("The generated PDF is incomplete; expected paper sections were not found.")

    print("Created {} ({} bytes)".format(OUTPUT_PATH, OUTPUT_PATH.stat().st_size))
    return OUTPUT_PATH


if __name__ == "__main__":
    main()
