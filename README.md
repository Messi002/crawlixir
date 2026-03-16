# Crawlixir

A web scraper that runs with a local AI (via [Ollama](https://ollama.com)). No API keys, no cloud. Scrape pages, pull out structured data, draft job application emails, and save them to your Gmail drafts. Everything stays on your machine.

## What it does

- Scrape any URL to markdown, HTML, text, or a list of links
- Crawl entire websites with depth control
- Find all URLs on a site
- Extract structured data from pages using a local LLM
- Pull text out of PDFs, DOCX files, and images (OCR)
- Watch pages for changes over time
- Draft job application emails from a posting + your CV
- Works from the terminal or as a Python library

## Check your hardware first

Not every machine can run every model. Run the hardware scanner to see what fits yours:

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/Messi002/crawlixir/main/crawlixir/hardware_scan.py | python3

# Windows (PowerShell)
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/Messi002/crawlixir/main/crawlixir/hardware_scan.py" -OutFile scan.py; python scan.py; Remove-Item scan.py
```

Or if you already cloned the repo:

```bash
python -m crawlixir.hardware_scan
```

## Installation

```bash
# 1. Install Ollama (if you haven't)
curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model (the scanner above will tell you which one)
ollama run llama3.2
```

Then install Crawlixir. Pick one:

```bash
# Option A: Install from PyPI (once published)
pip install crawlixir

# Option B: Install from source
git clone https://github.com/Messi002/crawlixir.git
cd crawlixir
pip install -e .
```

Optional, for JavaScript-heavy sites:
```bash
pip install playwright
playwright install chromium
```

## Gmail setup (optional, free)

If you want drafted emails to land in your Gmail drafts folder, you'll need to set up Google Cloud credentials. It takes about 15 minutes and costs nothing.

1. Go to [Google Cloud Console](https://console.cloud.google.com) and create a project (call it whatever you want)
2. Search for "Gmail API" and enable it
3. Go to APIs & Services, then Credentials. Create an OAuth 2.0 Client ID, pick "Desktop app" as the type
4. Download the JSON file Google gives you

Install the Gmail dependencies:

```bash
pip install -e ".[gmail]"
```

Then move your credentials file to where Crawlixir looks for it:

Linux / macOS:
```bash
mkdir -p ~/.crawlixir
cp client_secret_XXXXX.apps.googleusercontent.com.json ~/.crawlixir/credentials.json
```

Windows (PowerShell):
```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.crawlixir"
Copy-Item "client_secret_XXXXX.apps.googleusercontent.com.json" "$env:USERPROFILE\.crawlixir\credentials.json"
```

Windows (Command Prompt):
```cmd
mkdir "%USERPROFILE%\.crawlixir"
copy "client_secret_XXXXX.apps.googleusercontent.com.json" "%USERPROFILE%\.crawlixir\credentials.json"
```

Replace the filename with whatever Google named your download.

The first time you use `--gmail`, a browser window pops up asking you to authorize access. After that, it remembers you.

```bash
crawlixir scrape https://example.com/jobs/123 --ai --cv ~/my_cv.txt --gmail --to hr@company.com
```

The draft shows up in Gmail. You review it, tweak what you want, hit send.

Crawlixir only requests the `gmail.compose` scope. The code only creates drafts. It will never send anything on your behalf.

## Usage

### From the terminal

```bash
# Scrape a page to markdown
crawlixir scrape https://example.com

# Plain text instead
crawlixir scrape https://example.com -f text

# Save to a file
crawlixir scrape https://example.com -o output.md

# Scrape a job posting and draft an application email from your CV
crawlixir scrape https://example.com/jobs/123 --ai --cv ~/my_cv.txt

# Same thing with a PDF resume and a different model
crawlixir scrape https://example.com/jobs/123 --ai --cv ~/resume.pdf --model gemma2:2b

# Draft and save it straight to Gmail
crawlixir scrape https://example.com/jobs/123 --ai --cv ~/my_cv.txt --gmail --to hr@company.com

# Find all links on a site
crawlixir map https://example.com

# Crawl a site recursively (2 levels deep, up to 50 pages)
crawlixir crawl https://example.com -d 2 -m 50

# Pull specific info out of a page using AI
crawlixir extract https://example.com/jobs/123 -p "Extract job title, company, salary, and requirements"

# Check if a page changed since last time
crawlixir track https://example.com/pricing

# Get text from a PDF or image
crawlixir media resume.pdf
```

### As a Python library

```python
from crawlixir import Scraper, AI

scraper = Scraper()
result = scraper.scrape("https://example.com/jobs/123", fmt="text")
print(result["content"])

# Pull structured data out of the page
ai = AI(model="llama3.2")
data = ai.extract_json(
    result["content"],
    prompt="Extract job details",
    fields=["title", "company", "salary", "requirements"]
)
print(data)

# Draft a job application email
cv = open("my_cv.txt").read()
email = ai.draft_email(result["content"], cv)
print(email["subject"])
print(email["body"])
```

### Crawl a whole site

```python
from crawlixir.crawler import Crawler

crawler = Crawler(max_depth=2, max_pages=20)
pages = crawler.crawl("https://example.com")
for page in pages:
    print(page["metadata"]["title"])
```

### Watch a page for changes

```python
from crawlixir.tracker import Tracker

tracker = Tracker()
result = tracker.check("https://example.com/pricing")
if result["changed"]:
    print("Something changed:")
    print(result["diff"])
```

### Pull text from files

```python
from crawlixir import media

text = media.extract("resume.pdf")      # PDF
text = media.extract("document.docx")   # Word doc
text = media.extract("screenshot.png")  # OCR
```

## Models

Which model to use depends on your RAM and whether you have a GPU.

| Model | Params | Disk space | Good for |
|-------|--------|-----------|----------|
| `tinyllama` | 1.1B | ~0.6GB | Bare minimum hardware |
| `llama3.2:1b` | 1B | ~1.3GB | Quick, lightweight tasks |
| `gemma2:2b` | 2B | ~1.6GB | Solid reasoning for its size |
| `llama3.2` | 3B | ~2.0GB | Best tradeoff for most people |
| `qwen2.5:3b` | 3B | ~1.9GB | Coding and structured output |
| `mistral` | 7B | ~4.1GB | Needs 16GB RAM, worth it if you have it |
| `llama3.1:8b` | 8B | ~4.7GB | Better writing quality, same RAM requirement |

Run `python -m crawlixir.hardware_scan` if you're not sure.

## Roadmap

- [ ] Playwright for JS-heavy sites
- [x] Gmail draft integration
- [ ] Web search (query → scrape results → extract structured data)
- [ ] Export to CSV, JSON, and Excel
- [ ] Async batch scraping
- [ ] AI-powered bulk data collection (e.g. "find all scholarships in Europe")
- [ ] FastAPI server mode
- [ ] Browser extension
- [ ] Desktop GUI

## License

MIT
