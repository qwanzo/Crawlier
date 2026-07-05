from urllib.parse import urlparse, urlunparse


def normalize_url(url):
    """Normalize URLs so crawling and deduplication are consistent."""
    if not url:
        return ""

    try:
        parsed = urlparse(url.strip())
        if not parsed.scheme and not parsed.netloc:
            return url.strip()

        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        if scheme == 'http' and netloc.endswith(':80'):
            netloc = netloc[:-3]
        if scheme == 'https' and netloc.endswith(':443'):
            netloc = netloc[:-4]

        path = parsed.path or '/'
        if path != '/' and path.endswith('/'):
            path = path
        else:
            path = path or '/'
        return urlunparse((scheme, netloc, path, parsed.params, parsed.query, ''))
    except Exception:
        return url.strip()
