import os
import sqlite3


def init_database(crawler):
    """Initialize SQLite database for storing crawl data."""
    try:
        db_dir = os.path.dirname(crawler.db_file)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        crawler.db = sqlite3.connect(crawler.db_file, check_same_thread=False)
        cursor = crawler.db.cursor()
        table_schemas = {
            'urls': '''
                CREATE TABLE IF NOT EXISTS urls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE,
                    status_code INTEGER,
                    content_type TEXT,
                    size INTEGER,
                    depth INTEGER,
                    title TEXT,
                    description TEXT,
                    keywords TEXT,
                    h1_tags TEXT,
                    response_time REAL,
                    timestamp TEXT
                )
            ''',
            'keywords': '''
                CREATE TABLE IF NOT EXISTS keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT,
                    frequency INTEGER,
                    url TEXT
                )
            ''',
            'links': '''
                CREATE TABLE IF NOT EXISTS links (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_url TEXT,
                    target_url TEXT,
                    anchor_text TEXT,
                    link_type TEXT
                )
            ''',
            'technologies': '''
                CREATE TABLE IF NOT EXISTS technologies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    technology TEXT,
                    version TEXT
                )
            ''',
            'files': '''
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    file_type TEXT,
                    file_path TEXT,
                    file_size INTEGER
                )
            ''',
            'forms': '''
                CREATE TABLE IF NOT EXISTS forms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    action TEXT,
                    method TEXT,
                    fields TEXT
                )
            ''',
            'images': '''
                CREATE TABLE IF NOT EXISTS images (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    src TEXT,
                    alt TEXT,
                    title TEXT
                )
            ''',
            'subdomains': '''
                CREATE TABLE IF NOT EXISTS subdomains (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subdomain TEXT UNIQUE,
                    ip_address TEXT,
                    discovered_at TEXT
                )
            ''',
        }

        for schema in table_schemas.values():
            cursor.execute(schema)

        crawler.db.commit()
        print("[+] Database initialized")
    except Exception as exc:
        print(f"[-] Database initialization error: {exc}")


def queue_db_insert(crawler, sql, params):
    """Buffer small database writes and commit in batches for speed."""
    with crawler.db_lock:
        crawler._pending_db_ops.append((sql, params))
        if len(crawler._pending_db_ops) >= crawler._db_batch_size:
            flush_db_buffer(crawler)


def flush_db_buffer(crawler):
    """Commit pending database operations in one transaction."""
    if not crawler._pending_db_ops:
        return

    with crawler.db_lock:
        if not crawler._pending_db_ops:
            return
        cursor = crawler.db.cursor()
        for sql, params in crawler._pending_db_ops:
            cursor.execute(sql, params)
        crawler.db.commit()
        crawler._pending_db_ops.clear()
