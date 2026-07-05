
import sys
import io

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding.lower() in ['cp1252', 'utf-8']:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests
import re
import urllib.parse
import time
import json
import argparse
import sys
import os
import dns.resolver
import threading
from queue import Queue
from bs4 import BeautifulSoup, Comment
from urllib.robotparser import RobotFileParser
from collections import defaultdict, Counter
from datetime import datetime
import csv
from urllib.parse import urlparse, urljoin
import warnings

from .storage import init_database, queue_db_insert, flush_db_buffer
from .url_utils import normalize_url
from .parsing import parse_html
from .extractors import (
    analyze_seo,
    detect_technologies,
    extract_emails,
    extract_endpoints,
    extract_files,
    extract_forms,
    extract_headings,
    extract_images,
    extract_keywords,
    extract_metadata,
    extract_phone_numbers,
    extract_social_links,
    extract_structured_data,
    extract_videos,
)

warnings.filterwarnings('ignore')

class Crawlier:
    def __init__(self, target_domain, mode="pc", max_threads=10, delay=1, max_depth=3, 
                 respect_robots=True, captcha_solver=None, db_file="crawl_data.db"):
        """
        Initialize the Google-level web crawler
        
        Args:
            target_domain: Base domain to crawl
            mode: 'mobile' or 'pc' for user agent selection
            max_threads: Maximum number of concurrent threads
            delay: Delay between requests in seconds
            max_depth: Maximum crawl depth
            respect_robots: Whether to respect robots.txt
            captcha_solver: Optional captcha solving service API key
            db_file: SQLite database file for storing results
        """
        self.target_domain = target_domain
        self.mode = mode.lower()
        self.max_threads = max_threads
        self.delay = delay
        self.max_depth = max_depth
        self.respect_robots = respect_robots
        self.captcha_solver = captcha_solver
        self.db_file = db_file
        
        # User agents
        self.user_agents = {
            'mobile': 'MethmiBot/1.0 (Mobile; +http://github.com/yoohoo-dev/crawlier)',
            'pc': 'PansiluBot/1.0 (Desktop; +http://github.com/yoohoo-dev/crawlier)'
        }
        
        # Core data storage
        self.visited_urls = set()
        self.found_endpoints = set()
        self.found_subdomains = set()
        self.url_queue = Queue()
        self.results = defaultdict(dict)
        self.lock = threading.Lock()
        self.db_lock = threading.Lock()
        self._queued_urls = set()
        self._pending_db_ops = []
        self._db_batch_size = 50
        self._request_timestamps = {}
        self._rate_limit_lock = threading.Lock()
        
        # Advanced data extraction storage
        self.keywords = Counter()
        self.metadata = defaultdict(dict)
        self.page_content = defaultdict(str)
        self.structured_data = []
        self.social_links = defaultdict(set)
        self.technologies = defaultdict(set)
        self.emails = set()
        self.phone_numbers = set()
        self.files_found = defaultdict(list)
        self.forms = []
        self.seo_data = defaultdict(dict)
        self.site_structure = defaultdict(list)
        self.external_links = defaultdict(set)
        self.images = []
        self.videos = []
        self.scripts = defaultdict(list)
        self.stylesheets = defaultdict(list)
        self.api_endpoints = set()
        self.headers_data = defaultdict(dict)
        self.cookies_data = defaultdict(dict)
        self.redirects = defaultdict(list)
        self.performance_metrics = defaultdict(dict)
        
        # Language and content analysis
        self.languages_detected = Counter()
        self.content_types = Counter()
        
        # Error and performance tracking
        self.errors = defaultdict(int)
        self.crawl_start_time = None
        self.crawl_end_time = None
        self.response_times = []
        self.page_sizes = []
        self.status_codes = Counter()
        self.crawl_queue_size = 0
        self.peak_queue_size = 0
        
        # Initialize database
        self.db = None
        self._init_database()
        
        # Robots.txt parser
        self.robots_parser = None
        if self.respect_robots:
            self._load_robots_txt()
        
        # Session with retries
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(max_retries=3)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Common subdomains (compact)
        self.common_subdomains = """
        www mail ftp localhost webmail smtp pop ns1 webdisk ns2 cpanel whm autodiscover
        autoconfig m imap test ns blog pop3 dev www2 admin forum news vpn ns3 mail2
        new mysql old lists support mobile mx static docs beta shop sql secure demo cp
        calendar wiki web media email images img www1 intranet portal video sip dns2
        api cdn stats dns1 ns4 www3 dns search staging server mx1 chat wap my svn
        mail1 sites proxy ads host crm cms backup mx2 lyncdiscover info apps download
        remote db forums store relay files newsletter app live owa en start sms office
        exchange ipv4 gateway sandbox internal prod assets content data development git
        help id lab stage sso status upload v1 v2 ws academy account analytics
        """.split()
        
        # Technology fingerprints - compact regex per tech
        self.tech_fingerprints = {
            'WordPress': r'wp-content|wp-includes|wordpress',
            'Drupal': r'drupal|sites/default',
            'Joomla': r'joomla|components/com_',
            'React': r'react|reactdom',
            'Vue.js': r'vue\.js|vue\.min\.js',
            'Angular': r'angular|ng-',
            'jQuery': r'jquery',
            'Bootstrap': r'bootstrap',
            'Laravel': r'laravel',
            'Django': r'django|csrfmiddlewaretoken',
            'Flask': r'flask',
            'Node.js': r'X-Powered-By.*Express|X-Powered-By.*Node',
            'PHP': r'\.php|X-Powered-By.*PHP',
            'ASP.NET': r'aspx|X-AspNet-Version',
            'Cloudflare': r'cloudflare|cf-ray',
            'Google Analytics': r'google-analytics|gtag',
            'AWS': r'amazonaws\.com',
            'Apache': r'Server.*Apache',
            'Nginx': r'Server.*nginx',
        }
        
        # Stop words (compact)
        self.stop_words = set("the be to of and a in that have i it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way even new want because any these give day most us is are was were been has had did does being am".split())
    
    def _init_database(self):
        """Initialize SQLite database for storing crawl data"""
        init_database(self)
    
    def _load_robots_txt(self):
        """Load and parse robots.txt"""
        try:
            robots_url = f"https://{self.target_domain}/robots.txt"
            self.robots_parser = RobotFileParser()
            self.robots_parser.set_url(robots_url)
            self.robots_parser.read()
            print(f"[+] Loaded robots.txt from {robots_url}")
        except Exception as e:
            print(f"[-] Could not load robots.txt: {e}")
            print(f"[*] Continuing without robots.txt restrictions")
            self.robots_parser = None
    
    def _can_fetch(self, url):
        """Check if URL can be fetched according to robots.txt"""
        if not self.respect_robots or not self.robots_parser:
            return True
        return self.robots_parser.can_fetch(self.user_agents[self.mode], url)
    
    def _get_headers(self):
        """Get HTTP headers for requests"""
        return {
            'User-Agent': self.user_agents[self.mode],
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def _normalize_url(self, url):
        """Normalize URLs so crawling and deduplication are consistent."""
        return normalize_url(url)

    def _queue_url(self, url, depth):
        """Queue a URL only once, using normalized values for deduplication."""
        normalized = self._normalize_url(url)
        if not normalized:
            return False

        with self.lock:
            if normalized in self.visited_urls or normalized in self._queued_urls:
                return False
            self._queued_urls.add(normalized)
            self.url_queue.put((normalized, depth))
            self.crawl_queue_size = max(self.crawl_queue_size, self.url_queue.qsize())
            self.peak_queue_size = max(self.peak_queue_size, self.url_queue.qsize())
            return True

    def _queue_db_insert(self, sql, params):
        """Buffer small database writes and commit in batches for speed."""
        queue_db_insert(self, sql, params)

    def _flush_db_buffer(self):
        """Commit pending database operations in one transaction."""
        flush_db_buffer(self)

    def _maybe_enforce_delay(self, url):
        """Respect a minimum per-host delay without blocking unrelated hosts."""
        if self.delay <= 0:
            return

        hostname = urlparse(url).netloc or self.target_domain
        with self._rate_limit_lock:
            last_request = self._request_timestamps.get(hostname)
            wait_time = 0.0
            if last_request is not None:
                wait_time = max(0.0, self.delay - (time.monotonic() - last_request))
        if wait_time > 0:
            time.sleep(wait_time)

        with self._rate_limit_lock:
            self._request_timestamps[hostname] = time.monotonic()

    def _parse_html(self, html_content):
        """Parse HTML using lxml when available for better throughput."""
        return parse_html(html_content)
    
    def enumerate_subdomains(self):
        """Enumerate subdomains using DNS queries"""
        print(f"\n[*] Starting subdomain enumeration for {self.target_domain}")
        
        def check_subdomain(subdomain):
            try:
                full_domain = f"{subdomain}.{self.target_domain}"
                answers = dns.resolver.resolve(full_domain, 'A')
                if answers:
                    ip_address = str(answers[0])
                    with self.lock:
                        self.found_subdomains.add(full_domain)
                        print(f"[+] Found subdomain: {full_domain} ({ip_address})")
                        
                        # Store in database
                        self._queue_db_insert('''
                            INSERT OR IGNORE INTO subdomains (subdomain, ip_address, discovered_at)
                            VALUES (?, ?, ?)
                        ''', (full_domain, ip_address, datetime.now().isoformat()))
                    return full_domain
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.exception.Timeout):
                pass
            except Exception as e:
                pass
            return None
        
        threads = []
        for subdomain in self.common_subdomains:
            thread = threading.Thread(target=check_subdomain, args=(subdomain,))
            thread.start()
            threads.append(thread)
            
            if len(threads) >= self.max_threads:
                for t in threads:
                    t.join()
                threads = []
        
        for t in threads:
            t.join()
        
        print(f"[+] Found {len(self.found_subdomains)} subdomains")
        return list(self.found_subdomains)
    
    def extract_keywords(self, text, url, min_length=3, max_keywords=100):
        """Extract keywords from text content."""
        return extract_keywords(self, text, url, min_length=min_length, max_keywords=max_keywords)

    def _is_gibberish(self, word):
        """Backward-compatible wrapper for the legacy helper."""
        return extract_keywords.__globals__['_is_gibberish'](word)

    def extract_metadata(self, soup, url):
        """Extract metadata from HTML."""
        return extract_metadata(self, soup, url)

    def extract_headings(self, soup):
        """Extract all heading tags."""
        return extract_headings(soup)

    def detect_technologies(self, soup, headers, url):
        """Detect technologies used on the website."""
        return detect_technologies(self, soup, headers, url)

    def extract_emails(self, text):
        """Extract email addresses from text."""
        emails = extract_emails(text)
        with self.lock:
            self.emails.update(emails)
        return emails

    def extract_phone_numbers(self, text):
        """Extract phone numbers from text."""
        phones = extract_phone_numbers(text)
        with self.lock:
            self.phone_numbers.update(phones)
        return phones

    def extract_social_links(self, soup, url):
        """Extract social media links."""
        return extract_social_links(self, soup, url)

    def extract_forms(self, soup, url):
        """Extract form data."""
        return extract_forms(self, soup, url)

    def extract_images(self, soup, url):
        """Extract image data."""
        return extract_images(self, soup, url)

    def extract_videos(self, soup, url):
        """Extract video data."""
        return extract_videos(self, soup, url)

    def extract_structured_data(self, soup, url):
        """Extract structured data (JSON-LD, microdata)."""
        return extract_structured_data(self, soup, url)

    def extract_files(self, soup, url):
        """Extract downloadable files."""
        return extract_files(self, soup, url)

    def analyze_seo(self, soup, url, response):
        """Analyze SEO factors."""
        return analyze_seo(self, soup, url, response)

    def detect_captcha(self, response):
        """Detect if response contains a captcha"""
        # Check status code first - Cloudflare challenges are usually 403/503
        if response.status_code not in [403, 503]:
            # If status is 200, check content more carefully
            if response.status_code == 200:
                # Only flag as captcha if we see actual challenge elements
                captcha_indicators = [
                    'g-recaptcha', 'h-captcha', 'cf-challenge-form',
                    'challenge-platform', 'cf-chl-bypass'
                ]
                content_lower = response.text.lower()
                return any(indicator in content_lower for indicator in captcha_indicators)
            return False
        
        # For 403/503, check for actual captcha/challenge content
        captcha_indicators = [
            'recaptcha', 'captcha', 'g-recaptcha', 'hcaptcha', 'h-captcha',
            'cf-challenge', 'challenge-platform', 'checking your browser',
            'please verify you are human', 'cloudflare ray id'
        ]
        
        content_lower = response.text.lower()
        detected = sum(1 for indicator in captcha_indicators if indicator in content_lower)
        
        # Only flag as captcha if we have multiple indicators
        return detected >= 2
    
    def handle_captcha(self, url, response):
        """Attempt to handle captcha challenges"""
        print(f"[!] Captcha detected at {url}")
        
        if not self.captcha_solver:
            print("[!] No captcha solver configured. Skipping...")
            return None
        
        if 'recaptcha' in response.text.lower() or 'g-recaptcha' in response.text.lower():
            return self._solve_recaptcha(url, response)
        elif 'hcaptcha' in response.text.lower() or 'h-captcha' in response.text.lower():
            return self._solve_hcaptcha(url, response)
        elif 'cloudflare' in response.text.lower():
            return self._handle_cloudflare(url, response)
        
        return None
    
    def _solve_recaptcha(self, url, response):
        """Solve reCAPTCHA challenges"""
        print("[*] Attempting to solve reCAPTCHA...")
        site_key_match = re.search(r'data-sitekey="([^"]+)"', response.text)
        if not site_key_match:
            site_key_match = re.search(r'"sitekey":"([^"]+)"', response.text)
        
        if not site_key_match:
            print("[-] Could not find reCAPTCHA site key")
            return None
        
        site_key = site_key_match.group(1)
        print(f"[+] Found reCAPTCHA site key: {site_key}")
        print("[!] Captcha solving requires external service integration")
        return None
    
    def _solve_hcaptcha(self, url, response):
        """Solve hCaptcha challenges"""
        print("[*] Attempting to solve hCaptcha...")
        site_key_match = re.search(r'data-sitekey="([^"]+)"', response.text)
        if not site_key_match:
            print("[-] Could not find hCaptcha site key")
            return None
        
        site_key = site_key_match.group(1)
        print(f"[+] Found hCaptcha site key: {site_key}")
        print("[!] Captcha solving requires external service integration")
        return None
    
    def _handle_cloudflare(self, url, response):
        """Handle Cloudflare challenges"""
        print("[*] Detected Cloudflare challenge...")
        print("[!] Cloudflare bypass requires headless browser integration")
        return None
    
    def extract_endpoints(self, url, html_content):
        """Extract endpoints from HTML content."""
        return extract_endpoints(self, url, html_content)
    
    def crawl_url(self, url, depth=0):
        """Crawl a single URL with comprehensive data extraction"""
        normalized_url = self._normalize_url(url)
        if not normalized_url or depth > self.max_depth:
            return
        
        with self.lock:
            if normalized_url in self.visited_urls:
                return
            self.visited_urls.add(normalized_url)
            self._queued_urls.discard(normalized_url)
        
        if not self._can_fetch(normalized_url):
            print(f"[-] Blocked by robots.txt: {normalized_url}")
            print(f"[!] Tip: Use --no-robots flag to bypass (only if you have permission)")
            return
        
        try:
            self._maybe_enforce_delay(normalized_url)
            
            print(f"[*] Crawling [{depth}]: {normalized_url}")
            
            start_time = time.time()
            response = self.session.get(
                normalized_url, 
                headers=self._get_headers(),
                timeout=10,
                allow_redirects=True
            )
            response_time = time.time() - start_time
            
            # Track redirects
            if response.history:
                with self.lock:
                    self.redirects[normalized_url] = [self._normalize_url(r.url) for r in response.history]
            
            # Check for captcha
            if self.detect_captcha(response):
                captcha_response = self.handle_captcha(url, response)
                if not captcha_response:
                    return
                response = captcha_response
            
            # Store basic response info
            with self.lock:
                self.results[normalized_url] = {
                    'status_code': response.status_code,
                    'content_type': response.headers.get('Content-Type', ''),
                    'size': len(response.content),
                    'depth': depth,
                    'response_time': response_time,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Track performance metrics
                self.response_times.append(response_time)
                self.page_sizes.append(len(response.content))
                self.status_codes[response.status_code] += 1
                
                # Track content types
                content_type = response.headers.get('Content-Type', '').split(';')[0]
                self.content_types[content_type] += 1
                
                # Store headers
                self.headers_data[normalized_url] = dict(response.headers)
                
                # Store cookies
                self.cookies_data[normalized_url] = dict(response.cookies)
                
                # Performance metrics
                self.performance_metrics[normalized_url] = {
                    'response_time': response_time,
                    'size': len(response.content),
                    'size_kb': len(response.content) / 1024
                }
            
            # Only process HTML content
            if 'text/html' in response.headers.get('Content-Type', ''):
                print(f"[+] Processing HTML content from {normalized_url}")
                soup = self._parse_html(response.text)
                
                # Extract all data FIRST, before endpoint extraction
                print(f"    → Extracting metadata...")
                metadata = self.extract_metadata(soup, normalized_url)
                print(f"    → Extracting headings...")
                headings = self.extract_headings(soup)
                print(f"    → Extracting emails and phones...")
                self.extract_emails(response.text)
                self.extract_phone_numbers(response.text)
                print(f"    → Extracting social links...")
                self.extract_social_links(soup, normalized_url)
                print(f"    → Extracting forms...")
                self.extract_forms(soup, normalized_url)
                print(f"    → Extracting images...")
                self.extract_images(soup, normalized_url)
                print(f"    → Extracting videos...")
                self.extract_videos(soup, normalized_url)
                print(f"    → Extracting structured data...")
                self.extract_structured_data(soup, normalized_url)
                print(f"    → Extracting files...")
                self.extract_files(soup, normalized_url)
                print(f"    → Analyzing SEO...")
                seo = self.analyze_seo(soup, normalized_url, response)
                
                # Extract keywords from visible text
                print(f"    → Extracting keywords...")
                keywords = self.extract_keywords(response.text, normalized_url)
                print(f"    → Found {len(keywords)} unique keywords")
                
                # Detect technologies
                print(f"    → Detecting technologies...")
                technologies = self.detect_technologies(soup, response.headers, normalized_url)
                if technologies:
                    print(f"    → Detected: {', '.join(technologies)}")
                
                # Store page content
                with self.lock:
                    self.page_content[normalized_url] = soup.get_text(' ', strip=True)[:10000]  # First 10k chars
                
                # Store in database
                try:
                    self._queue_db_insert('''
                        INSERT OR REPLACE INTO urls 
                        (url, status_code, content_type, size, depth, title, description, keywords, h1_tags, response_time, timestamp)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        normalized_url, 
                        response.status_code,
                        response.headers.get('Content-Type', ''),
                        len(response.content),
                        depth,
                        metadata.get('title', ''),
                        metadata.get('description', ''),
                        metadata.get('keywords', ''),
                        json.dumps(headings.get('h1', [])),
                        response_time,
                        datetime.now().isoformat()
                    ))
                    print(f"    → Saved to database")
                except Exception as e:
                    print(f"[!] Database error for {normalized_url}: {e}")
                
                # Extract and queue new endpoints (do this LAST)
                print(f"    → Discovering new endpoints...")
                endpoints = self.extract_endpoints(normalized_url, response.text)
                print(f"    → Found {len(endpoints)} endpoints")
                
                with self.lock:
                    self.found_endpoints.update(endpoints)
                
                # Add new endpoints to queue for crawling
                new_urls = 0
                for endpoint in endpoints:
                    if self._queue_url(endpoint, depth + 1):
                        new_urls += 1
                
                if new_urls > 0:
                    print(f"    → Queued {new_urls} new URLs for crawling")
                
            else:
                content_type = response.headers.get('Content-Type', 'unknown')
                print(f"[-] Skipping non-HTML content: {content_type}")
            
        except requests.exceptions.RequestException as e:
            error_type = type(e).__name__
            with self.lock:
                self.errors[error_type] += 1
                self.results[normalized_url] = {
                    'error': str(e),
                    'error_type': error_type,
                    'depth': depth,
                    'timestamp': datetime.now().isoformat()
                }
            print(f"[-] Error crawling {normalized_url}: {e}")
        except Exception as e:
            error_type = type(e).__name__
            with self.lock:
                self.errors[error_type] += 1
                self.results[normalized_url] = {
                    'error': str(e),
                    'error_type': error_type,
                    'depth': depth,
                    'timestamp': datetime.now().isoformat()
                }
            print(f"[-] Unexpected error at {normalized_url}: {e}")
    
    def worker(self):
        """Worker thread for crawling"""
        while True:
            try:
                # Track queue size
                current_queue_size = self.url_queue.qsize()
                with self.lock:
                    self.peak_queue_size = max(self.peak_queue_size, current_queue_size)
                
                url, depth = self.url_queue.get(timeout=5)
                with self.lock:
                    self._queued_urls.discard(url)
                self.crawl_url(url, depth)
                self.url_queue.task_done()
            except:
                break
    
    def start_crawl(self):
        """Start the crawling process"""
        self.crawl_start_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"Starting {'MethmiBot' if self.mode == 'mobile' else 'PansiluBot'}")
        print(f"Google-Level Web Crawler")
        print(f"Target: {self.target_domain}")
        print(f"Mode: {self.mode.upper()}")
        print(f"Max Threads: {self.max_threads}")
        print(f"Max Depth: {self.max_depth}")
        print(f"{'='*60}\n")
        
        # Step 1: Enumerate subdomains
        subdomains = self.enumerate_subdomains()
        
        # Step 2: Start crawling
        start_urls = [f"https://{self.target_domain}"]
        start_urls.extend([f"https://{sub}" for sub in subdomains])
        
        for url in start_urls:
            self._queue_url(url, 0)
        
        # Step 3: Start worker threads
        threads = []
        for _ in range(self.max_threads):
            thread = threading.Thread(target=self.worker)
            thread.daemon = True
            thread.start()
            threads.append(thread)
        
        # Wait for queue to be empty
        self.url_queue.join()
        
        # Stop workers
        for thread in threads:
            thread.join(timeout=1)
        
        self._flush_db_buffer()
        self.crawl_end_time = time.time()
        
        print(f"\n{'='*60}")
        print(f"Crawl completed!")
        print(f"{'='*60}")
        self.print_statistics()
    
    def print_statistics(self):
        """Print comprehensive crawl statistics"""
        total_time = self.crawl_end_time - self.crawl_start_time if self.crawl_end_time and self.crawl_start_time else 0
        
        print(f"\n📊 COMPREHENSIVE CRAWL STATISTICS:")
        print(f"  🕐 Total Crawl Time: {total_time:.2f} seconds")
        print(f"  📈 URLs Visited: {len(self.visited_urls)}")
        print(f"  🔗 Endpoints Found: {len(self.found_endpoints)}")
        print(f"  🌐 Subdomains Found: {len(self.found_subdomains)}")
        print(f"  🔍 Keywords Extracted: {len(self.keywords)}")
        print(f"  📧 Emails Found: {len(self.emails)}")
        print(f"  📞 Phone Numbers Found: {len(self.phone_numbers)}")
        print(f"  📝 Forms Found: {len(self.forms)}")
        print(f"  🖼️  Images Found: {len(self.images)}")
        print(f"  🎥 Videos Found: {len(self.videos)}")
        print(f"  📄 Files Found: {sum(len(files) for files in self.files_found.values())}")
        print(f"  🔗 API Endpoints: {len(self.api_endpoints)}")
        
        # Performance metrics
        if self.response_times:
            avg_response = sum(self.response_times) / len(self.response_times)
            print(f"  ⚡ Average Response Time: {avg_response:.3f} seconds")
            print(f"  🏃 Fastest Response: {min(self.response_times):.3f} seconds")
            print(f"  🐌 Slowest Response: {max(self.response_times):.3f} seconds")
        
        if self.page_sizes:
            avg_size = sum(self.page_sizes) / len(self.page_sizes)
            total_size = sum(self.page_sizes)
            print(f"  📊 Average Page Size: {avg_size/1024:.1f} KB")
            print(f"  💾 Total Data Downloaded: {total_size/1024/1024:.1f} MB")
        
        # Queue statistics
        print(f"  📋 Peak Queue Size: {self.peak_queue_size}")
        
        # Status codes
        if self.status_codes:
            print(f"  📊 HTTP Status Codes:")
            for code, count in sorted(self.status_codes.items()):
                print(f"    {code}: {count}")
        
        # Error statistics
        if self.errors:
            print(f"  ❌ Errors Encountered: {sum(self.errors.values())}")
            for error_type, count in sorted(self.errors.items()):
                print(f"    {error_type}: {count}")
        
        # Content types
        if self.content_types:
            print(f"  📋 Content Types:")
            for ct, count in sorted(self.content_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"    {ct}: {count}")
        
        print(f"\n🔧 TECHNOLOGIES DETECTED:")
        all_tech = set()
        for tech_set in self.technologies.values():
            all_tech.update(tech_set)
        if all_tech:
            for tech in sorted(all_tech):
                print(f"  - {tech}")
        else:
            print("  - None detected")
        
        print(f"\n📱 SOCIAL MEDIA:")
        social_count = 0
        for platform, links in self.social_links.items():
            if links:
                print(f"  {platform.title()}: {len(links)} link(s)")
                social_count += len(links)
        if social_count == 0:
            print("  - No social media links found")
        
        print(f"\n🔝 TOP 20 KEYWORDS:")
        if self.keywords:
            for keyword, count in self.keywords.most_common(20):
                print(f"  {keyword}: {count}")
        else:
            print("  - No keywords extracted")
    
    def save_results(self, output_file='crawl_results.json'):
        """Save comprehensive crawl results - merges with existing data"""
        output = {
            'target_domain': self.target_domain,
            'crawler_mode': self.mode,
            'crawler_name': 'MethmiBot' if self.mode == 'mobile' else 'PansiluBot',
            'timestamp': datetime.now().isoformat(),
            'statistics': {
                'total_urls_visited': len(self.visited_urls),
                'total_endpoints_found': len(self.found_endpoints),
                'total_subdomains_found': len(self.found_subdomains),
                'total_keywords': len(self.keywords),
                'unique_emails': len(self.emails),
                'unique_phones': len(self.phone_numbers),
                'forms_found': len(self.forms),
                'images_found': len(self.images),
                'videos_found': len(self.videos),
                'files_found': sum(len(files) for files in self.files_found.values()),
                'api_endpoints': len(self.api_endpoints),
                'total_crawl_time': self.crawl_end_time - self.crawl_start_time if self.crawl_end_time and self.crawl_start_time else 0,
                'average_response_time': sum(self.response_times) / len(self.response_times) if self.response_times else 0,
                'min_response_time': min(self.response_times) if self.response_times else 0,
                'max_response_time': max(self.response_times) if self.response_times else 0,
                'average_page_size': sum(self.page_sizes) / len(self.page_sizes) if self.page_sizes else 0,
                'total_data_downloaded': sum(self.page_sizes),
                'peak_queue_size': self.peak_queue_size,
                'http_status_codes': dict(self.status_codes),
                'errors': dict(self.errors),
                'content_types': dict(self.content_types)
            },
            'subdomains': sorted(list(self.found_subdomains)),
            'endpoints': sorted(list(self.found_endpoints))[:1000],  # Limit to first 1000
            'top_keywords': dict(self.keywords.most_common(100)),
            'technologies': {url: list(techs) for url, techs in self.technologies.items()},
            'emails': sorted(list(self.emails)),
            'phone_numbers': sorted(list(self.phone_numbers)),
            'social_links': {platform: sorted(list(links)) for platform, links in self.social_links.items()},
            'forms': self.forms,
            'files': {file_type: files for file_type, files in self.files_found.items()},
            'api_endpoints': sorted(list(self.api_endpoints)),
            'content_types': dict(self.content_types),
            'seo_data': {url: data for url, data in list(self.seo_data.items())[:100]},  # Limit
            'url_details': {url: data for url, data in list(self.results.items())[:500]}  # Limit
        }
        
        # Load existing data and merge
        if os.path.exists(output_file):
            try:
                with open(output_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                
                # Merge statistics (add current to existing) - only numeric keys are summed
                existing_stats = existing.get('statistics', {})
                for key, val in existing_stats.items():
                    try:
                        if isinstance(val, (int, float)):
                            output['statistics'][key] = output['statistics'].get(key, 0) + val
                        else:
                            # preserve existing non-numeric values if output doesn't have them
                            output['statistics'].setdefault(key, val)
                    except Exception:
                        # fallback: keep output's value
                        continue
                
                # Merge lists/sets
                output['subdomains'] = sorted(list(set(existing.get('subdomains', []) + output['subdomains'])))
                output['endpoints'] = sorted(list(set(existing.get('endpoints', []) + output['endpoints'])))
                output['emails'] = sorted(list(set(existing.get('emails', []) + output['emails'])))
                output['phone_numbers'] = sorted(list(set(existing.get('phone_numbers', []) + output['phone_numbers'])))
                output['api_endpoints'] = sorted(list(set(existing.get('api_endpoints', []) + output['api_endpoints'])))
                
                # Merge keywords (combine counters)
                existing_keywords = existing.get('top_keywords', {})
                combined_keywords = Counter(existing_keywords)
                combined_keywords.update(self.keywords)
                output['top_keywords'] = dict(combined_keywords.most_common(100))
                
                # Merge technologies
                existing_tech = existing.get('technologies', {})
                existing_tech.update(output['technologies'])
                output['technologies'] = existing_tech
                
                # Merge social links
                existing_social = existing.get('social_links', {})
                for platform, links in existing_social.items():
                    if platform in output['social_links']:
                        output['social_links'][platform] = sorted(list(set(links + output['social_links'][platform])))
                    else:
                        output['social_links'][platform] = links
                
                # Merge forms, files, etc.
                output['forms'] = existing.get('forms', []) + output['forms']
                output['files'] = {**existing.get('files', {}), **output['files']}
                
                # Merge content types
                existing_content_types = existing.get('content_types', {})
                for ct, count in existing_content_types.items():
                    output['content_types'][ct] = output['content_types'].get(ct, 0) + count
                
                # Merge SEO data and URL details
                existing_seo = existing.get('seo_data', {})
                existing_seo.update(output['seo_data'])
                output['seo_data'] = existing_seo
                
                existing_urls = existing.get('url_details', {})
                existing_urls.update(output['url_details'])
                output['url_details'] = existing_urls
                
                # Update timestamp to latest
                output['timestamp'] = datetime.now().isoformat()
                
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[!] Warning: Could not merge with existing data ({e}). Overwriting...")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:  # Only create directories if there's a directory path
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n[+] Results saved to {output_file}")
        
        # Create detailed report
        report_file = output_file.replace('.json', '_report.txt')
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(f"{'='*80}\n")
                f.write(f"{'MethmiBot' if self.mode == 'mobile' else 'PansiluBot'} - Google-Level Crawl Report\n")
                f.write(f"{'='*80}\n\n")
                f.write(f"Target Domain: {self.target_domain}\n")
                f.write(f"Crawl Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Mode: {self.mode.upper()}\n")
                f.write(f"Database: {self.db_file}\n\n")
                
                f.write(f"{'='*80}\n")
                f.write(f"STATISTICS\n")
                f.write(f"{'='*80}\n")
                for key, value in output['statistics'].items():
                    f.write(f"  {key.replace('_', ' ').title()}: {value}\n")
                
                f.write(f"\n{'='*80}\n")
                f.write(f"SUBDOMAINS ({len(self.found_subdomains)})\n")
                f.write(f"{'='*80}\n")
                for subdomain in sorted(self.found_subdomains):
                    f.write(f"  - {subdomain}\n")
                
                f.write(f"\n{'='*80}\n")
                f.write(f"TOP 50 KEYWORDS\n")
                f.write(f"{'='*80}\n")
                for keyword, count in self.keywords.most_common(50):
                    try:
                        f.write(f"  {keyword}: {count}\n")
                    except UnicodeEncodeError:
                        # Skip keywords that can't be encoded
                        continue
                
                f.write(f"\n{'='*80}\n")
                f.write(f"TECHNOLOGIES DETECTED\n")
                f.write(f"{'='*80}\n")
                all_tech = set()
                for tech_set in self.technologies.values():
                    all_tech.update(tech_set)
                for tech in sorted(all_tech):
                    f.write(f"  - {tech}\n")
                
                f.write(f"\n{'='*80}\n")
                f.write(f"EMAILS FOUND ({len(self.emails)})\n")
                f.write(f"{'='*80}\n")
                for email in sorted(self.emails):
                    f.write(f"  - {email}\n")
                
                f.write(f"\n{'='*80}\n")
                f.write(f"SOCIAL MEDIA LINKS\n")
                f.write(f"{'='*80}\n")
                for platform, links in self.social_links.items():
                    if links:
                        f.write(f"\n  {platform.title()}:\n")
                        for link in sorted(links):
                            f.write(f"    - {link}\n")
                
                f.write(f"\n{'='*80}\n")
                f.write(f"FILES FOUND\n")
                f.write(f"{'='*80}\n")
                for file_type, files in self.files_found.items():
                    f.write(f"\n  {file_type.upper()} Files ({len(files)}):\n")
                    for file_path in files[:20]:  # Limit to 20 per type
                        f.write(f"    - {file_path}\n")
                
                f.write(f"\n{'='*80}\n")
                f.write(f"API ENDPOINTS ({len(self.api_endpoints)})\n")
                f.write(f"{'='*80}\n")
                for endpoint in sorted(self.api_endpoints):
                    f.write(f"  - {endpoint}\n")
            
            print(f"[+] Report saved to {report_file}")
        except Exception as e:
            print(f"[!] Warning: Could not create text report: {e}")
            print(f"[+] Data is still available in JSON and database files")
        
        # Create CSV export
        csv_file = output_file.replace('.json', '_urls.csv')
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['URL', 'Status Code', 'Content Type', 'Size (bytes)', 'Depth', 'Response Time', 'Title'])
            
            for url, data in self.results.items():
                title = self.metadata.get(url, {}).get('title', '')
                writer.writerow([
                    url,
                    data.get('status_code', ''),
                    data.get('content_type', ''),
                    data.get('size', ''),
                    data.get('depth', ''),
                    data.get('response_time', ''),
                    title
                ])
        
        print(f"[+] CSV export saved to {csv_file}")
        print(f"[+] Database saved to {self.db_file}")
    
    def close(self):
        """Close database connection"""
        if self.db:
            self.db.close()


def main():
    parser = argparse.ArgumentParser(
        description='MethmiBot (Mobile) / PansiluBot (PC)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic crawl
  python python_file_name.py -d example.com -m pc
  
  # Deep crawl with high concurrency
  python python_file_name.py -d example.com -m mobile -t 20 --delay 0.5 --depth 5
  
  # Crawl without respecting robots.txt
  python python_file_name.py -d example.com -m pc --no-robots
        """
    )
    
    parser.add_argument('-d', '--domain', required=True, help='Target domain to crawl')
    parser.add_argument('-m', '--mode', choices=['mobile', 'pc'], default='pc',
                       help='Crawler mode: mobile (MethmiBot) or pc (PansiluBot)')
    parser.add_argument('-t', '--threads', type=int, default=10,
                       help='Maximum number of concurrent threads (default: 10)')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--depth', type=int, default=3,
                       help='Maximum crawl depth (default: 3)')
    parser.add_argument('--no-robots', action='store_true',
                       help='Ignore robots.txt rules')
    parser.add_argument('--captcha-key', help='API key for captcha solving service')
    parser.add_argument('-o', '--output', default='crawl_results.json',
                       help='Output file for results (default: crawl_results.json)')
    parser.add_argument('--db', default='crawl_data.db',
                       help='SQLite database file (default: crawl_data.db)')
    
    args = parser.parse_args()
    
    domain = args.domain.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
    
    try:
        crawler = Crawlier(
            target_domain=domain,
            mode=args.mode,
            max_threads=args.threads,
            delay=args.delay,
            max_depth=args.depth,
            respect_robots=not args.no_robots,
            captcha_solver=args.captcha_key,
            db_file=args.db
        )
        
        crawler.start_crawl()
        crawler.save_results(args.output)
        crawler.close()
        
    except KeyboardInterrupt:
        print("\n[!] Crawl interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def run_crawl(url, mode="pc", max_threads=5, delay=1, max_depth=2, ignore_robots=False):
    """
    Run crawl and yield live logs for Gradio UI.
    Returns final JSON results at the end.
    """
    domain = url.replace('http://', '').replace('https://', '').replace('www.', '').split('/')[0]
    crawler = Crawlier(
        target_domain=domain,
        mode=mode,
        max_threads=max_threads,
        delay=delay,
        max_depth=max_depth,
        respect_robots=not ignore_robots
    )

    logs_queue = Queue()

    def log(message):
        logs_queue.put(message)

    # Patch builtin print
    import builtins
    original_print = builtins.print
    builtins.print = log

    def crawl_generator():
        import threading

        def crawl_thread():
            try:
                crawler.start_crawl()
                crawler.save_results("output/crawl_results.json")
                crawler.close()
                logs_queue.put("DONE")
            except Exception as e:
                logs_queue.put(f"Error: {e}")

        t = threading.Thread(target=crawl_thread)
        t.start()

        while t.is_alive() or not logs_queue.empty():
            try:
                message = logs_queue.get(timeout=0.1)
                yield message
            except:
                pass

        t.join()

    result = crawl_generator()
    
    # Restore builtin print
    builtins.print = original_print
    
    return result


if __name__ == '__main__':
    main()

