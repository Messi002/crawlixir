from setuptools import setup, find_packages

setup(
    name="crawlixir",
    version="0.1.0",
    description="Web scraper with local AI support via Ollama",
    author="",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "requests",
        "beautifulsoup4",
        "markdownify",
        "aiohttp",
        "pdfplumber",
        "python-docx",
        "pytesseract",
        "Pillow",
        "psutil",
    ],
    extras_require={
        "browser": ["playwright"],
        "gmail": [
            "google-auth",
            "google-auth-oauthlib",
            "google-api-python-client",
        ],
        "all": [
            "playwright",
            "duckduckgo-search",
            "google-auth",
            "google-auth-oauthlib",
            "google-api-python-client",
        ],
    },
    entry_points={
        "console_scripts": [
            "crawlixir=crawlixir.cli:main",
        ],
    },
)
