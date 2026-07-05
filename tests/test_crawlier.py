"""Unit tests for the optimized crawler."""

import tempfile
import unittest

from crawlier.crawler import Crawlier


class TestCrawlierOptimization(unittest.TestCase):
    def test_initialization_sets_default_runtime_state(self):
        crawler = Crawlier("example.com", max_threads=3, delay=0.1, max_depth=2)

        self.assertEqual(crawler.target_domain, "example.com")
        self.assertEqual(crawler.max_threads, 3)
        self.assertEqual(crawler.max_depth, 2)
        self.assertTrue(crawler.visited_urls is not None)
        self.assertTrue(crawler.url_queue is not None)

    def test_normalize_url_removes_fragments_and_normalizes_paths(self):
        crawler = Crawlier("example.com", max_threads=1, delay=0.0, max_depth=1)

        normalized = crawler._normalize_url("https://example.com/path/?x=1#section")

        self.assertEqual(normalized, "https://example.com/path/?x=1")

    def test_queue_url_deduplicates_before_enqueue(self):
        crawler = Crawlier("example.com", max_threads=1, delay=0.0, max_depth=1)

        self.assertTrue(crawler._queue_url("https://example.com", 0))
        self.assertFalse(crawler._queue_url("https://example.com", 0))
        self.assertEqual(crawler.url_queue.qsize(), 1)

    def test_database_and_results_paths_are_created(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as handle:
            db_path = handle.name

        try:
            crawler = Crawlier("example.com", max_threads=1, delay=0.0, max_depth=1, db_file=db_path)
            self.assertTrue(crawler.db is not None)
            self.assertTrue(crawler.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='urls'").fetchone())
        finally:
            crawler.close()
            import os
            if os.path.exists(db_path):
                os.remove(db_path)
