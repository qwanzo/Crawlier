import json
import re
from collections import Counter, defaultdict
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Comment

from .storage import queue_db_insert


def _is_gibberish(word):
    """Check if word looks like gibberish."""
    if len(word) < 3:
        return True

    vowels = sum(1 for c in word if c in 'aeiou')
    vowel_ratio = vowels / len(word)
    if vowel_ratio < 0.2 and len(word) > 4:
        return True

    if len(set(word)) < len(word) / 3:
        return True

    return False


def extract_keywords(crawler, text, url, min_length=3, max_keywords=100):
    """Extract keywords from text content."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'[^\w\s]', ' ', text.lower())

    words = text.split()
    keywords = []
    for word in words:
        if len(word) < min_length:
            continue
        if word in crawler.stop_words:
            continue
        if not word.isascii():
            continue
        if word.isdigit():
            continue
        if _is_gibberish(word):
            continue
        keywords.append(word)

    word_freq = Counter(keywords)
    with crawler.lock:
        crawler.keywords.update(word_freq)
        rows = [(k, f, url) for k, f in word_freq.most_common(max_keywords)]
        for row in rows:
            queue_db_insert(crawler, '''
                INSERT INTO keywords (keyword, frequency, url) VALUES (?, ?, ?)
            ''', row)

    return word_freq.most_common(max_keywords)


def extract_metadata(crawler, soup, url):
    """Extract metadata from HTML."""
    metadata = {}
    title_tag = soup.find('title')
    metadata['title'] = title_tag.get_text().strip() if title_tag else ''

    meta_tags = soup.find_all('meta')
    for tag in meta_tags:
        name = tag.get('name', tag.get('property', ''))
        content = tag.get('content', '')
        if name and content:
            metadata[name.lower()] = content

    desc_tag = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
    metadata['description'] = desc_tag.get('content', '') if desc_tag else ''

    keywords_tag = soup.find('meta', attrs={'name': 'keywords'})
    metadata['keywords'] = keywords_tag.get('content', '') if keywords_tag else ''

    og_tags = {}
    for tag in meta_tags:
        prop = tag.get('property', '')
        if prop.startswith('og:'):
            og_tags[prop] = tag.get('content', '')
    metadata['open_graph'] = og_tags

    twitter_tags = {}
    for tag in meta_tags:
        name = tag.get('name', '')
        if name.startswith('twitter:'):
            twitter_tags[name] = tag.get('content', '')
    metadata['twitter'] = twitter_tags

    canonical = soup.find('link', attrs={'rel': 'canonical'})
    metadata['canonical'] = canonical.get('href', '') if canonical else ''

    html_tag = soup.find('html')
    metadata['language'] = html_tag.get('lang', '') if html_tag else ''

    with crawler.lock:
        crawler.metadata[url] = metadata

    return metadata


def extract_headings(soup):
    """Extract all heading tags."""
    headings = defaultdict(list)
    for index in range(1, 7):
        tags = soup.find_all(f'h{index}')
        headings[f'h{index}'] = [tag.get_text().strip() for tag in tags]
    return dict(headings)


def detect_technologies(crawler, soup, headers, url):
    """Detect technologies used on the website."""
    technologies = set()
    html_content = str(soup)
    for tech, pattern in crawler.tech_fingerprints.items():
        if re.search(pattern, html_content, re.IGNORECASE):
            technologies.add(tech)

    for tech, pattern in crawler.tech_fingerprints.items():
        for header, value in headers.items():
            if re.search(pattern, f"{header}: {value}", re.IGNORECASE):
                technologies.add(tech)
                break

    with crawler.lock:
        crawler.technologies[url].update(technologies)
        for tech in technologies:
            queue_db_insert(crawler, '''
                INSERT INTO technologies (url, technology, version)
                VALUES (?, ?, ?)
            ''', (url, tech, ''))

    return list(technologies)


def extract_emails(text):
    """Extract email addresses from text."""
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    return re.findall(email_pattern, text)


def extract_phone_numbers(text):
    """Extract phone numbers from text."""
    patterns = [
        r'\+?1?\d{9,15}',
        r'\(\d{3}\)\s*\d{3}-\d{4}',
        r'\d{3}-\d{3}-\d{4}',
        r'\d{3}\.\d{3}\.\d{4}'
    ]
    phones = []
    for pattern in patterns:
        phones.extend(re.findall(pattern, text))
    return phones


def extract_social_links(crawler, soup, url):
    """Extract social media links."""
    social_platforms = {
        'facebook': r'facebook\.com',
        'twitter': r'twitter\.com|x\.com',
        'instagram': r'instagram\.com',
        'linkedin': r'linkedin\.com',
        'youtube': r'youtube\.com',
        'tiktok': r'tiktok\.com',
        'pinterest': r'pinterest\.com',
        'github': r'github\.com',
        'reddit': r'reddit\.com'
    }

    links = soup.find_all('a', href=True)
    for link in links:
        href = link['href']
        full = urljoin(url, href)
        for platform, pattern in social_platforms.items():
            if re.search(pattern, full, re.IGNORECASE):
                with crawler.lock:
                    crawler.social_links[platform].add(full)


def extract_forms(crawler, soup, url):
    """Extract form data."""
    forms = soup.find_all('form')
    for form in forms:
        form_data = {
            'url': url,
            'action': form.get('action', ''),
            'method': form.get('method', 'get').upper(),
            'fields': []
        }
        inputs = form.find_all(['input', 'select', 'textarea'])
        for inp in inputs:
            field = {
                'type': inp.get('type', inp.name),
                'name': inp.get('name', ''),
                'id': inp.get('id', ''),
                'required': inp.has_attr('required')
            }
            form_data['fields'].append(field)

        with crawler.lock:
            crawler.forms.append(form_data)
            queue_db_insert(crawler, '''
                INSERT INTO forms (url, action, method, fields)
                VALUES (?, ?, ?, ?)
            ''', (url, form_data['action'], form_data['method'], json.dumps(form_data['fields'])))


def extract_images(crawler, soup, url):
    """Extract image data."""
    images = soup.find_all('img')
    for img in images:
        img_data = {
            'url': url,
            'src': urljoin(url, img.get('src', '')),
            'alt': img.get('alt', ''),
            'title': img.get('title', ''),
            'width': img.get('width', ''),
            'height': img.get('height', '')
        }
        with crawler.lock:
            crawler.images.append(img_data)
            queue_db_insert(crawler, '''
                INSERT INTO images (url, src, alt, title)
                VALUES (?, ?, ?, ?)
            ''', (url, img_data['src'], img_data['alt'], img_data['title']))


def extract_videos(crawler, soup, url):
    """Extract video data."""
    videos = soup.find_all(['video', 'iframe'])
    for video in videos:
        video_data = {'url': url, 'src': video.get('src', ''), 'type': video.name}
        if video.name == 'iframe':
            src = video.get('src', '')
            if 'youtube.com' in src or 'vimeo.com' in src:
                video_data['platform'] = 'youtube' if 'youtube' in src else 'vimeo'
        with crawler.lock:
            crawler.videos.append(video_data)


def extract_structured_data(crawler, soup, url):
    """Extract structured data (JSON-LD, microdata)."""
    structured = []
    scripts = soup.find_all('script', type='application/ld+json')
    for script in scripts:
        try:
            data = json.loads(script.string)
            structured.append({'type': 'json-ld', 'data': data})
        except Exception:
            pass

    with crawler.lock:
        if structured:
            crawler.structured_data.extend(structured)
    return structured


def extract_files(crawler, soup, url):
    """Extract downloadable files."""
    file_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip', '.rar', '.tar', '.gz', '.csv', '.txt', '.xml', '.json']
    links = soup.find_all('a', href=True)
    for link in links:
        href = link['href']
        for ext in file_extensions:
            if ext in href.lower():
                full_url = urljoin(url, href)
                file_type = ext[1:]
                with crawler.lock:
                    crawler.files_found[file_type].append(full_url)
                    queue_db_insert(crawler, '''
                        INSERT INTO files (url, file_type, file_path, file_size)
                        VALUES (?, ?, ?, ?)
                    ''', (url, file_type, full_url, 0))
                break


def analyze_seo(crawler, soup, url, response):
    """Analyze SEO factors."""
    seo = {}
    title = soup.find('title')
    title_text = title.get_text().strip() if title else ''
    seo['title'] = {'text': title_text, 'length': len(title_text), 'optimal': 50 <= len(title_text) <= 60}

    desc = soup.find('meta', attrs={'name': 'description'})
    desc_text = desc.get('content', '') if desc else ''
    seo['description'] = {'text': desc_text, 'length': len(desc_text), 'optimal': 150 <= len(desc_text) <= 160}

    h1_tags = soup.find_all('h1')
    seo['h1'] = {'count': len(h1_tags), 'texts': [h.get_text().strip() for h in h1_tags], 'optimal': len(h1_tags) == 1}

    images = soup.find_all('img')
    images_without_alt = [img for img in images if not img.get('alt')]
    seo['images'] = {'total': len(images), 'without_alt': len(images_without_alt), 'alt_percentage': (len(images) - len(images_without_alt)) / len(images) * 100 if images else 0}

    seo['page_size'] = {'bytes': len(response.content), 'kb': len(response.content) / 1024, 'optimal': len(response.content) < 3 * 1024 * 1024}
    seo['response_time'] = {'seconds': response.elapsed.total_seconds(), 'optimal': response.elapsed.total_seconds() < 3}
    seo['https'] = url.startswith('https')
    viewport = soup.find('meta', attrs={'name': 'viewport'})
    seo['mobile_friendly'] = viewport is not None

    links = soup.find_all('a', href=True)
    internal = sum(1 for link in links if crawler.target_domain in link['href'])
    external = len(links) - internal
    seo['links'] = {'total': len(links), 'internal': internal, 'external': external}

    with crawler.lock:
        crawler.seo_data[url] = seo
    return seo


def extract_endpoints(crawler, url, html_content):
    """Extract endpoints from HTML content."""
    soup = BeautifulSoup(html_content, 'html.parser')
    endpoints = set()

    for tag in soup.find_all(['a', 'link']):
        href = tag.get('href')
        if href:
            endpoints.add(href)
            anchor_text = tag.get_text().strip() if tag.name == 'a' else ''
            link_type = 'internal' if crawler.target_domain in href else 'external'
            with crawler.lock:
                queue_db_insert(crawler, '''
                    INSERT INTO links (source_url, target_url, anchor_text, link_type)
                    VALUES (?, ?, ?, ?)
                ''', (url, href, anchor_text, link_type))

    for tag in soup.find_all('script'):
        src = tag.get('src')
        if src:
            endpoints.add(src)

    for tag in soup.find_all('img'):
        src = tag.get('src')
        if src:
            endpoints.add(src)

    for tag in soup.find_all('form'):
        action = tag.get('action')
        if action:
            endpoints.add(action)

    scripts = soup.find_all('script', string=True)
    for script in scripts:
        urls = re.findall(r'["\']([^"\']*?\.(?:html|php|asp|aspx|jsp|json|xml|js|css)[^"\']*?)["\']', str(script.string))
        endpoints.update(urls)

        api_urls = re.findall(r'["\']/?(?:api|v\d+)/[^"\']+["\']', str(script.string))
        api_clean = [u.strip('"\'') for u in api_urls]
        endpoints.update(api_clean)
        with crawler.lock:
            crawler.api_endpoints.update(api_clean)

    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for comment in comments:
        urls = re.findall(r'https?://[^\s<>"\']+|www\.[^\s<>"\']+', str(comment))
        endpoints.update(urls)

    normalized = set()
    for endpoint in endpoints:
        try:
            normalized_url = urljoin(url, endpoint)
            parsed = urlparse(normalized_url)
            if crawler.target_domain in parsed.netloc or any(sub in parsed.netloc for sub in crawler.found_subdomains):
                normalized.add(normalized_url)
            else:
                with crawler.lock:
                    crawler.external_links[url].add(normalized_url)
        except Exception:
            pass

    return normalized
