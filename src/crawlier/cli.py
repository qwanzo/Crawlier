"""
Unified CLI for Crawlier - Terminal and Batch modes
"""
import sys
import io

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding.lower() in ['cp1252']:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import argparse

# Import crawler modules
from crawlier.app.terminal_crawler import main as terminal_main
from crawlier.app.batch_crawler import main as batch_main


def main():
    """Main CLI entry point for Crawlier"""
    parser = argparse.ArgumentParser(
        description='Crawlier - Advanced Web Crawler (Terminal or Batch mode)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Terminal mode (interactive, single domain)
  crawlier -d example.com -m pc
  crawlier -d example.com -m mobile --depth 5
  
  # Batch mode (process queue file)
  crawlier -b
  crawlier -b --mode mobile --threads 10
  crawlier -b --add example.com example2.com
  crawlier -b --show
        """
    )
    
    # Add mode selection (terminal or batch)
    parser.add_argument('-b', '--batch', action='store_true',
                       help='Run in batch mode (process crawl_queue.txt)')
    
    # Terminal mode options
    parser.add_argument('-d', '--domain', help='Target domain to crawl (terminal mode)')
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
    parser.add_argument('-o', '--output', default='crawl_results.json',
                       help='Output file for results (terminal mode)')
    parser.add_argument('--db', default='crawl_data.db',
                       help='SQLite database file (default: crawl_data.db)')
    
    # Batch mode options
    parser.add_argument('--queue', default='crawl_queue.txt',
                       help='Queue file path (batch mode, default: crawl_queue.txt)')
    parser.add_argument('--add', nargs='+', metavar='DOMAIN',
                       help='Add domains to queue (batch mode)')
    parser.add_argument('--show', action='store_true',
                       help='Show current queue (batch mode)')
    
    args = parser.parse_args()
    
    try:
        if args.batch:
            # Batch mode
            batch_argv = ['batch_crawler.py']
            
            if args.add:
                batch_argv.extend(['--add'] + args.add)
            elif args.show:
                batch_argv.append('--show')
            else:
                # Run batch processing
                batch_argv.append('--process')
                batch_argv.extend(['--mode', args.mode])
                batch_argv.extend(['--threads', str(args.threads)])
                batch_argv.extend(['--delay', str(args.delay)])
                batch_argv.extend(['--depth', str(args.depth)])
                if args.no_robots:
                    batch_argv.append('--no-robots')
                batch_argv.extend(['--queue', args.queue])
            
            sys.argv = batch_argv
            batch_main()
        else:
            # Terminal mode
            if not args.domain:
                parser.print_help()
                print("\n[ERROR] Terminal mode requires --domain (-d) argument")
                sys.exit(1)
            
            terminal_argv = ['crawlier']
            terminal_argv.extend(['-d', args.domain])
            terminal_argv.extend(['-m', args.mode])
            terminal_argv.extend(['-t', str(args.threads)])
            terminal_argv.extend(['--delay', str(args.delay)])
            terminal_argv.extend(['--depth', str(args.depth)])
            if args.no_robots:
                terminal_argv.append('--no-robots')
            terminal_argv.extend(['-o', args.output])
            terminal_argv.extend(['--db', args.db])
            
            sys.argv = terminal_argv
            terminal_main()
    
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
