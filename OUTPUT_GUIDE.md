# Crawlier Output Guide

## Output File Locations

By default, output files are created in the **current working directory**. However, you can specify a custom output directory using the `-o` parameter.

### Using Output Directory (-o flag)

The crawler automatically creates the output directory if it doesn't exist:

```bash
# Creates ./output/ directory and saves files there
crawlier -d example.com -o output/crawl_results.json

# Creates ./results/2026-02 directory and saves files there
crawlier -d example.com -o results/2026-02/crawl_results.json
```

### Default Behavior (No -o specified)

When you run without specifying output:
```bash
crawlier -d example.com
```

Files are created in the **current working directory**:
```
.
├── crawl_results.json
├── crawl_results_report.txt
├── crawl_results_urls.csv
└── crawl_data.db
```

### With Output Directory Specified

When you run with `-o output/crawl_results.json`:
```bash
crawlier -d example.com -o output/crawl_results.json
```

Files are created in the **output/ subdirectory**:
```
.
└── output/
    ├── crawl_results.json
    ├── crawl_results_report.txt
    └── crawl_results_urls.csv
```

The SQLite database file (specified with `--db`) is saved to its own location:
```bash
crawlier -d example.com -o output/crawl_results.json --db output/crawl_data.db
```

## Output Files Details

#### 1. JSON Format (`crawl_results.json`)
```json
{
  "target_domain": "example.com",
  "crawler_mode": "pc",
  "timestamp": "2026-02-05T17:39:56",
  "statistics": {
    "total_urls_visited": 2,
    "total_keywords": 31,
    "unique_emails": 0,
    ...
  },
  "top_keywords": {...},
  "technologies": {...},
  "subdomains": [...],
  "endpoints": [...]
}
```

#### 2. Report Format (`crawl_results_report.txt`)
```
================================================================================
PansiluBot - Google-Level Crawl Report
================================================================================

Target Domain: example.com
Crawl Date: 2026-02-05 17:39:56
Mode: PC

================================================================================
STATISTICS
================================================================================
  Total Urls Visited: 2
  Total Keywords: 31
  ...
```

#### 3. CSV Format (`crawl_results_urls.csv`)
```csv
url,status_code,title,content_type,size
https://example.com,200,Example Domain,text/html,512
https://www.example.com,200,Example Domain,text/html,512
```

#### 4. Database Format (`crawl_data.db`)
SQLite database with tables:
- `crawl_pages` — All pages crawled
- `crawl_keywords` — Extracted keywords
- `crawl_technologies` — Detected technologies
- `crawl_subdomains` — Found subdomains
- And more...

Query with SQL:
```bash
sqlite3 crawl_data.db "SELECT url, status_code FROM crawl_pages LIMIT 10;"
```

### Accessing Results in Python

```python
from crawlier import Crawlier
import json

# Run crawl
crawler = Crawlier(target_domain="example.com")
crawler.start_crawl()

# Save to specific location
crawler.save_results("my_results/example_crawl.json")

# Or read the generated JSON
with open("crawl_results.json") as f:
    data = json.load(f)
    print(f"Found {len(data['top_keywords'])} keywords")
```

### Combining Results from Multiple Crawls

The SQLite database accumulates results:
```bash
# First crawl
crawlier -d example.com

# Second crawl (adds to same database)
crawlier -d example2.com --db crawl_data.db

# Query combined results
sqlite3 crawl_data.db "SELECT DISTINCT domain FROM crawl_pages;"
```

### Pro Tips

1. **Organize by date**: Create dated directories
   ```bash
   mkdir crawl_$(date +%Y%m%d)
   cd crawl_$(date +%Y%m%d)
   crawlier -d example.com
   ```

2. **Archive results**: Compress old crawls
   ```bash
   zip -r crawl_2026_02_05.zip crawl_results.* crawl_data.db
   ```

3. **Compare crawls**: Keep separate databases
   ```bash
   crawlier -d example.com --db crawl_2026_01.db
   crawlier -d example.com --db crawl_2026_02.db
   sqlite3 -batch <<< "
     SELECT COUNT(*) FROM 'crawl_2026_01.db'.crawl_keywords;
     SELECT COUNT(*) FROM 'crawl_2026_02.db'.crawl_keywords;
   "
   ```

4. **Export to other formats**: Use Python to transform
   ```python
   import json
   import csv
   
   with open("crawl_results.json") as f:
       data = json.load(f)
   
   # Convert to CSV
   with open("keywords.csv", "w") as f:
       writer = csv.writer(f)
       writer.writerow(["keyword", "count"])
       for kw, count in data["top_keywords"].items():
           writer.writerow([kw, count])
   ```

---

**Summary**: Output files go to your **current working directory** by default. Use `-o` and `--db` flags to customize locations.
