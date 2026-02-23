# Crawlier — v1.0

> A modern, high-performance web crawler library built entirely in Python.  
> Supports desktop (PansiluBot) and mobile (MethmiBot) crawling modes with comprehensive data extraction.

---

## What is Crawlier?

Crawlier is a powerful Python web crawler designed for comprehensive website analysis and data extraction. It includes:

- **Terminal Mode**: Single-domain crawling with detailed extraction
- **Batch Mode**: Queue-based multi-domain crawling with progress tracking
- **Technology Detection**: Identify frameworks, platforms, and tools
- **SEO Analysis**: Analyze title, description, headings, and optimization metrics
- **Comprehensive Extraction**: Keywords, emails, phones, forms, images, videos, social links, and more

Perfect for reconnaissance, competitive analysis, data research, and automated site inventory.

## Features

✨ **Core Crawling**
- Multi-threaded crawling (configurable concurrency)
- Configurable crawl depth and request delay
- Optional `robots.txt` respect (toggleable)
- Automatic redirect handling and session management

📊 **Data Extraction**
- Metadata (title, description, OG tags, Twitter cards)
- Keywords with frequency analysis
- Emails and phone numbers (regex-based)
- Social media links (9+ platforms)
- Forms with field mapping
- Images, videos, and structured data
- Downloadable files (PDF, DOC, ZIP, etc.)
- API endpoints from JavaScript

🔧 **Advanced Features**
- Technology fingerprinting (WordPress, Django, React, etc.)
- SEO metrics (page size, response time, HTTPS, mobile-friendly)
- Subdomain enumeration (DNS-based)
- CAPTCHA detection (reCAPTCHA, hCaptcha, Cloudflare)
- SQLite database storage with detailed reporting
- JSON/CSV export formats

---

## Installation

### From PyPI (Recommended)
```bash
pip install crawlier
```

### From Source (Development)
```bash
git clone https://github.com/Qwanzo/Crawlier.git
cd Crawlier
pip install -e .
```

**Requirements:** Python 3.10+

---

## CLI Usage

### Terminal Mode (Single Domain)

Crawl a single domain with detailed extraction:

```bash
# Basic crawl
crawlier -d example.com

# With mobile user agent
crawlier -d example.com -m mobile

# Deep crawl with high concurrency
crawlier -d example.com -m mobile -t 20 --delay 0.5 --depth 5

# Ignore robots.txt (only if permitted)
crawlier -d example.com --no-robots

# Custom output and database
crawlier -d example.com -o results.json --db crawl.db
```

### Batch Mode (Multiple Domains)

Process domains from a queue file:

```bash
# Process all domains in crawl_queue.txt
crawlier -b

# Add domains to queue
crawlier -b --add example.com example2.com example3.com

# Show current queue
crawlier -b --show

# Process with custom settings
crawlier -b --mode mobile --threads 10 --depth 3
```

### CLI Options

**Terminal Mode (-d/--domain required):**
- `-d, --domain` : Target domain (required for terminal mode)
- `-m, --mode` : `mobile` or `pc` (default: `pc`)
- `-t, --threads` : Max concurrent threads (default: 10)
- `--delay` : Seconds between requests (default: 1.0)
- `--depth` : Maximum crawl depth (default: 3)
- `--no-robots` : Ignore `robots.txt` rules
- `-o, --output` : Output JSON file (default: `crawl_results.json`)
- `--db` : SQLite database file (default: `crawl_data.db`)

**Batch Mode (-b flag):**
- `--add DOMAIN [DOMAIN ...]` : Add domains to queue
- `--show` : Display queue contents
- `--process` : Process queue (default behavior)
- `-m, --mode` : `mobile` or `pc` (default: `pc`)
- `-t, --threads` : Max threads per domain (default: 5)
- `--depth` : Max depth per domain (default: 2)
- `--queue` : Queue file path (default: `crawl_queue.txt`)
- `--no-robots` : Ignore `robots.txt` for all domains

### Output Files

By default, all output files are generated in the **current working directory** where you run the command.

**Generated files:**

- **`crawl_results.json`** — Complete crawl data in JSON format
  - All extracted metadata, keywords, technologies, endpoints
  - Statistics (timing, response codes, page sizes)
  - Structured data for programmatic processing

- **`crawl_results_report.txt`** — Human-readable text report
  - Summary statistics
  - Lists of subdomains, top keywords, technologies detected
  - HTTP status codes and error summary
  - Best for quick review of results

- **`crawl_results_urls.csv`** — CSV export of discovered URLs
  - One URL per line with metadata
  - Importable into spreadsheet applications
  - Useful for further analysis

- **`crawl_data.db`** — SQLite database
  - Detailed records of all pages crawled
  - Queryable with SQL for custom analysis
  - Persists across multiple crawls (data is appended)

**Custom output locations:**

```bash
# Save to specific directory
crawlier -d example.com -o ./results/my_crawl.json --db ./results/crawl.db

# Change output filename
crawlier -d example.com -o results_2026.json
```

**Batch mode output:**

When using batch mode, each domain gets its own output files:
- `crawl_results_{domain}_report.txt`
- `crawl_results_{domain}_urls.csv`
- `crawl_results_{domain}.json`

All stored in the project root or your specified output directory.

---

## Python API

### Using the Crawlier Class

Import and use the main `Crawlier` class:

```python
from crawlier import Crawlier

# Create crawler instance
crawler = Crawlier(
    target_domain="example.com",
    mode="pc",                    # or "mobile"
    max_threads=10,
    delay=1.0,
    max_depth=3,
    respect_robots=True,
    db_file="crawl_data.db"
)

# Run the crawl
crawler.start_crawl()

# Save results
crawler.save_results("output/my_results.json")

# Clean up
crawler.close()
```

### Generator-based Crawling (Streaming Logs)

For UIs that need live progress updates (like Gradio):

```python
from crawlier import run_crawl

for log_line in run_crawl(
    url="https://example.com",
    mode="pc",
    max_threads=5,
    max_depth=2,
    ignore_robots=False
):
    print(log_line)  # Real-time output
```

### Accessing Extracted Data

After crawling, access results via crawler attributes:

```python
# Visit statistics
print(f"URLs visited: {len(crawler.visited_urls)}")
print(f"Endpoints found: {len(crawler.found_endpoints)}")
print(f"Subdomains: {crawler.found_subdomains}")

# Extracted data
print(f"Emails: {crawler.emails}")
print(f"Phone numbers: {crawler.phone_numbers}")
print(f"Keywords: {crawler.keywords.most_common(20)}")
print(f"Technologies: {list(crawler.technologies.values())}")

# Forms, images, videos
print(f"Forms found: {len(crawler.forms)}")
print(f"Images: {len(crawler.images)}")
print(f"Videos: {len(crawler.videos)}")

# Performance metrics
print(f"Total time: {crawler.crawl_end_time - crawler.crawl_start_time:.2f}s")
print(f"Average response time: {sum(crawler.response_times) / len(crawler.response_times):.3f}s")
```

---

## Output Examples

### JSON Structure

```json
{
  "target_domain": "example.com",
  "crawler_mode": "pc",
  "crawler_name": "PansiluBot",
  "timestamp": "2026-02-05T12:34:56.789123",
  "statistics": {
    "total_urls_visited": 42,
    "total_endpoints_found": 156,
    "total_subdomains_found": 8,
    "unique_emails": 3,
    "unique_phones": 2,
    "api_endpoints": 12,
    "average_response_time": 0.453
  },
  "subdomains": ["www.example.com", "api.example.com", ...],
  "top_keywords": {
    "example": 24,
    "service": 18,
    "product": 15
  },
  "emails": ["contact@example.com", ...],
  "technologies": {
    "https://example.com": ["React", "Node.js", "AWS"]
  },
  "social_links": {
    "twitter": ["https://twitter.com/example"],
    "linkedin": ["https://linkedin.com/company/example"]
  }
}
```

### Report File

```
============================================================
PansiluBot - Google-Level Crawl Report
============================================================

Target Domain: example.com
Crawl Date: 2026-02-05 12:34:56
Mode: PC

============================================================
STATISTICS
============================================================
  Total Urls Visited: 42
  Total Endpoints Found: 156
  Total Subdomains Found: 8
  ...
```

---

## Use Cases

📱 **SEO & Site Analysis**
- Audit website structure and metadata
- Identify broken links and redirects
- Analyze internal linking strategy
- Check mobile-friendliness markers

🔍 **Competitive Intelligence**
- Detect competitor technologies
- Find API endpoints and integrations
- Discover subdomains and infrastructure
- Extract keywords and content themes

🛡️ **Security Assessment**
- Identify technologies for targeted research
- Find exposed endpoints and forms
- Enumerate subdomains for attack surface
- Collect contact information

📊 **Data Research**
- Build datasets of company websites
- Extract structured information at scale
- Monitor site changes over time
- Generate inventory reports

---

## Architecture

```
src/crawlier/
├── __init__.py           # Package initialization & exports
├── crawler.py            # Main Crawlier class (1500+ lines)
├── cli.py                # Unified CLI entry point
└── app/
    ├── terminal_crawler.py    # Single-domain terminal mode
    └── batch_crawler.py       # Multi-domain batch processing
```

---

## Configuration

### robots.txt Respect

By default, Crawlier respects `robots.txt`. Disable only if you have permission:

```python
crawler = Crawlier(
    target_domain="example.com",
    respect_robots=False  # ⚠️ Only with permission!
)
```

CLI equivalent:
```bash
crawlier -d example.com --no-robots
```

### Threading

Adjust concurrency based on your needs and target capacity:

```python
crawler = Crawlier(target_domain="example.com", max_threads=20)  # High concurrency
crawler = Crawlier(target_domain="example.com", max_threads=3)   # Respectful crawling
```

### Request Delay

Add delays between requests to reduce server load:

```bash
crawlier -d example.com --delay 2.0  # 2 seconds between requests
```

---

## Limitations & Notes

- ⚠️ **JavaScript**: Static HTML only; JavaScript-rendered content not supported
- ⚠️ **CAPTCHA**: Basic detection implemented; solving requires external service integration
- ⚠️ **Authentication**: Cookie-aware but not credential-protected
- ⚠️ **Rate Limiting**: No built-in backoff; respect server load with `--delay` and `--threads`
- ⚠️ **Legal**: Always verify you have permission to crawl target sites

---

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License — See [LICENSE](LICENSE) for details.

---

## Authors

**Pansilu Chethiya** (yoohoo-dev)  
Email: pansiluco@gmail.com  
GitHub: [@Qwanzo](https://github.com/Qwanzo)

Organization: Pansilu Inc

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and planned features.
	captcha_solver=None,
	db_file="crawl_data.db"
)

crawler.start_crawl()
crawler.save_results("crawl_results.json")
crawler.close()
```

---

## Output

Crawlier writes:

- JSON output (default `crawl_results.json`)
- CSV export of URL details
- An SQLite DB (default `crawl_data.db`)
- A human-friendly text report alongside JSON (if enabled)

Make sure the `output/` directory exists before running, or provide a path that does.

---

## Example: `run_crawl()` with mobile UA

```python
for log in run_crawl(
	url="https://example.com",
	mode="mobile",
	max_threads=10,
	delay=0.5,
	max_depth=3,
	ignore_robots=False
):
	print(log)
```

---

## Documentation

Comprehensive guides and documentation:

- **[CHANGELOG.md](CHANGELOG.md)** — Version history and release notes
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — How to contribute to Crawlier
- **[OUTPUT_GUIDE.md](OUTPUT_GUIDE.md)** — Understanding output files and formats
- **[OUTPUT_DIRECTORY_GUIDE.md](OUTPUT_DIRECTORY_GUIDE.md)** — Using custom output directories
- **[OUTPUT_VERIFICATION.md](OUTPUT_VERIFICATION.md)** — Output functionality verification

---

## License

Crawlier is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## Authors & Credits

**Pansilu Chethiya (yoohoo-dev)**  
Email: pansiluco@gmail.com  
Organization: Pansilu Inc  
GitHub: [@Qwanzo](https://github.com/Qwanzo)

---

## Repository

- **GitHub Repository**: [Qwanzo/Crawlier](https://github.com/Qwanzo/Crawlier)
- **Bug Reports**: [Issues](https://github.com/Qwanzo/Crawlier/issues)
- **PyPI Package**: [crawlier](https://pypi.org/project/crawlier/)

Enjoy using Crawlier! 🚀
