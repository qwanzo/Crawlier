from bs4 import BeautifulSoup


def parse_html(html_content):
    """Parse HTML with lxml when available for better throughput."""
    try:
        return BeautifulSoup(html_content, 'lxml')
    except Exception:
        return BeautifulSoup(html_content, 'html.parser')
