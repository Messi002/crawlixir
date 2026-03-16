"""CLI for Crawlixir."""

import argparse
import json
import sys
from .scraper import Scraper
from .ai import AI
from .crawler import Crawler
from .tracker import Tracker
from . import media


def main():
    parser = argparse.ArgumentParser(
        prog="crawlixir",
        description="Web scraper with local AI support",
    )
    sub = parser.add_subparsers(dest="command")

    # scrape
    sp = sub.add_parser("scrape", help="Scrape a URL")
    sp.add_argument("url", help="URL to scrape")
    sp.add_argument("-f", "--format", default="markdown", choices=["markdown", "text", "html", "links"])
    sp.add_argument("-o", "--output", help="Save output to file")
    sp.add_argument("--ai", action="store_true", help="Use local AI to draft an application email")
    sp.add_argument("--cv", help="Path to your CV/resume file (txt, pdf, docx)")
    sp.add_argument("--model", default="llama3.2", help="Ollama model to use (default: llama3.2)")
    sp.add_argument("--to", help="Recipient email address")
    sp.add_argument("--gmail", action="store_true", help="Save the drafted email as a Gmail draft")
    sp.add_argument("--instructions", default="", help="Extra instructions for the AI")

    # crawl
    cp = sub.add_parser("crawl", help="Crawl a website recursively")
    cp.add_argument("url", help="Starting URL")
    cp.add_argument("-d", "--depth", type=int, default=2, help="Max crawl depth")
    cp.add_argument("-m", "--max-pages", type=int, default=50, help="Max pages to crawl")
    cp.add_argument("-o", "--output", help="Save output to file")

    # map
    mp = sub.add_parser("map", help="Discover all URLs on a website")
    mp.add_argument("url", help="URL to map")

    # extract
    ep = sub.add_parser("extract", help="AI-extract info from a URL")
    ep.add_argument("url", help="URL to scrape and extract from")
    ep.add_argument("-p", "--prompt", required=True, help="What to extract")
    ep.add_argument("--model", default="llama3.2", help="Ollama model to use")

    # track
    tp = sub.add_parser("track", help="Check a URL for changes")
    tp.add_argument("url", help="URL to track")

    # media
    medp = sub.add_parser("media", help="Extract text from PDF, DOCX, or image")
    medp.add_argument("file", help="Path to file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "scrape":
        result = Scraper().scrape(args.url, fmt=args.format)
        output = result["content"] if isinstance(result["content"], str) else json.dumps(result["content"], indent=2)

        if args.ai:
            # Load CV
            if not args.cv:
                print("Error: --ai requires --cv <path-to-your-cv>")
                sys.exit(1)

            cv_path = args.cv
            if cv_path.endswith((".pdf", ".docx", ".png", ".jpg", ".jpeg")):
                cv_content = media.extract(cv_path)
            else:
                with open(cv_path, "r") as f:
                    cv_content = f.read()

            # Draft email using local AI
            ai = AI(model=args.model)
            print("Drafting email with local AI... (this may take a moment)")
            email = ai.draft_email(
                job_content=output,
                cv_content=cv_content,
                recipient_email=args.to,
                extra_instructions=args.instructions,
            )

            print(f"\n--- SUBJECT ---\n{email['subject']}")
            print(f"\n--- BODY ---\n{email['body']}")

            # Save to Gmail drafts if requested
            if args.gmail:
                from .gmail import create_draft
                print("\nSaving to Gmail drafts...")
                draft = create_draft(
                    subject=email["subject"],
                    body=email["body"],
                    to=args.to,
                )
                print(f"Draft saved! Open it here: {draft['url']}")

            # Also save to file if requested
            if args.output:
                with open(args.output, "w") as f:
                    f.write(f"Subject: {email['subject']}\n\n{email['body']}")
                print(f"\nEmail saved to {args.output}")
        else:
            if args.output:
                with open(args.output, "w") as f:
                    f.write(output)
                print(f"Saved to {args.output}")
            else:
                print(output)

    elif args.command == "crawl":
        crawler = Crawler(max_depth=args.depth, max_pages=args.max_pages)
        results = crawler.crawl(args.url)
        output = json.dumps(results, indent=2, default=str)
        if args.output:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Crawled {len(results)} pages. Saved to {args.output}")
        else:
            print(f"Crawled {len(results)} pages.")
            for r in results:
                src = r.get("metadata", {}).get("source_url", r.get("source_url", "?"))
                print(f"  - {src}")

    elif args.command == "map":
        result = Crawler().map(args.url)
        print(f"Found {result['total']} links ({len(result['internal'])} internal, {len(result['external'])} external)")
        for link in result["internal"]:
            print(f"  [internal] {link['url']}")
        for link in result["external"][:10]:
            print(f"  [external] {link['url']}")

    elif args.command == "extract":
        scraper = Scraper()
        ai = AI(model=args.model)
        result = scraper.scrape(args.url, fmt="text")
        extracted = ai.extract(result["content"], args.prompt)
        print(extracted)

    elif args.command == "track":
        result = Tracker().check(args.url)
        print(result["message"])
        if result["changed"]:
            print(result["diff"])

    elif args.command == "media":
        text = media.extract(args.file)
        print(text)


if __name__ == "__main__":
    main()
