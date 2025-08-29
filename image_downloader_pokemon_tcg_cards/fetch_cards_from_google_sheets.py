# Extracts Pokemon card image URLs from Google Sheets IMAGE formulas and saves to Python file
import re
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIG ---
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1iYtq1A1RZhYMmWoawIVkVGMZxo3CLu_nkCpzSBpoJFs/edit"
CREDENTIALS_FILE = "google-cloud-credentials.json"
OUTPUT_PY = "image_urls.py"

# --- AUTH ---
creds = Credentials.from_service_account_file(
    CREDENTIALS_FILE,
    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
)
gc = gspread.authorize(creds)

# --- OPEN SHEET ---
ss = gc.open_by_url(SPREADSHEET_URL)

# Regex: capture the first quoted URL inside =IMAGE("..."), case-insensitive
URL_RE = re.compile(r'"(https?://[^"]+)"', re.IGNORECASE)

all_urls = []

for sh in ss.worksheets():
    # Get entire Column D as FORMULAS (not displayed values)
    # Using sheet.row_count ensures we cover the full used range height
    rng = f"D1:D{sh.row_count}"
    rows = sh.get(rng, value_render_option="FORMULA", major_dimension="ROWS")

    # rows is a list like [["=IMAGE(\"https://...\")"], [""], ...]
    for row in rows:
        if not row:  # empty row array
            continue
        cell = row[0] or ""  # the formula or empty string
        # Look only at IMAGE formulas
        if cell.strip().upper().startswith("=IMAGE("):
            m = URL_RE.search(cell)
            if m:
                all_urls.append(m.group(1))

print(f"✅ Found {len(all_urls)} image URLs across all sheets")

# Optional: dedupe while preserving order
seen = set()
deduped = []
for u in all_urls:
    if u not in seen:
        seen.add(u)
        deduped.append(u)

with open(OUTPUT_PY, "w", encoding="utf-8") as f:
    f.write("image_urls = [\n")
    for url in deduped:
        f.write(f'    "{url}",\n')
    f.write("]\n")

print(f"✅ Wrote {len(deduped)} URLs to {OUTPUT_PY}")
