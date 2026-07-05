import unittest

from crawlier import Crawlier


class TestCrawlier(unittest.TestCase):
    def test_init(self):
        crawler = Crawlier("example.com")
        self.assertEqual(crawler.target_domain, "example.com")

    def test_run_crawl_does_not_require_network_for_init(self):
        crawler = Crawlier("example.com", max_threads=1, max_depth=1)
        self.assertEqual(crawler.max_depth, 1)


if __name__ == "__main__":
    unittest.main()
