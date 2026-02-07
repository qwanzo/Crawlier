
import sys
import io

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding.lower() in ['cp1252']:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from crawlier.crawler import Crawlier
import argparse


def main():
    """Terminal mode main function"""
    parser = argparse.ArgumentParser(
        description='Crawlier Terminal Mode - Single Domain Crawler',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  crawlier -d example.com -m pc
  crawlier -d example.com -m mobile --depth 5 -t 20
  crawlier -d example.com --no-robots -o my_results.json
        """
    )
    
    parser.add_argument('-d', '--domain', required=True, help='Target domain to crawl')
    parser.add_argument('-m', '--mode', choices=['mobile', 'pc'], default='pc',
                       help='Crawler mode')
    parser.add_argument('-t', '--threads', type=int, default=10,
                       help='Max threads')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between requests')
    parser.add_argument('--depth', type=int, default=3,
                       help='Max crawl depth')
    parser.add_argument('--no-robots', action='store_true',
                       help='Ignore robots.txt')
    parser.add_argument('-o', '--output', default='crawl_results.json',
                       help='Output file')
    parser.add_argument('--db', default='crawl_data.db',
                       help='Database file')
    
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


if __name__ == '__main__':
    main()
