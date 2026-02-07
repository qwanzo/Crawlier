
import sys
import io

# Fix Windows console encoding for Unicode support
if sys.stdout.encoding.lower() in ['cp1252']:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os
import time
from crawlier.crawler import Crawlier
import argparse


def load_queue(queue_file="crawl_queue.txt"):
    """Load domains from queue file"""
    if not os.path.exists(queue_file):
        print(f"[!] Queue file {queue_file} not found. Creating empty queue.")
        with open(queue_file, "w") as f:
            f.write("# Add domains to crawl, one per line\n")
        return []
    
    with open(queue_file, "r") as f:
        lines = f.read().splitlines()
    
    domains = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            domains.append(line)
    
    return domains


def save_queue(domains, queue_file="crawl_queue.txt"):
    """Save remaining domains to queue file"""
    with open(queue_file, "w") as f:
        f.write("# Crawl queue - domains to process\n")
        f.write("# Format: domain\n")
        for domain in domains:
            f.write(f"{domain}\n")


def crawl_domain(domain, mode="pc", max_threads=5, delay=1, max_depth=2, respect_robots=True):
    """Crawl a single domain"""
    print(f"[*] Starting crawl for: {domain}")
    
    try:
        crawler = Crawlier(
            target_domain=domain,
            mode=mode,
            max_threads=max_threads,
            delay=delay,
            max_depth=max_depth,
            respect_robots=respect_robots
        )
        
        crawler.start_crawl()
        safe_domain = domain.replace('.', '_')
        crawler.save_results(f"output/crawl_results_{safe_domain}.json")
        crawler.close()
        
        print(f"[+] Completed crawl for: {domain}")
        return True
        
    except Exception as e:
        print(f"[-] Failed to crawl {domain}: {e}")
        return False


def process_queue(queue_file="crawl_queue.txt", mode="pc", max_threads=5, delay=1, max_depth=2, respect_robots=True):
    """Process all domains in the queue"""
    domains = load_queue(queue_file)
    
    if not domains:
        print("[!] Queue is empty. Add domains to crawl_queue.txt")
        return
    
    start_time = time.time()
    
    print(f"[*] Found {len(domains)} domains in queue")
    for i, domain in enumerate(domains, 1):
        print(f"  {i}. {domain}")
    
    print(f"\n[*] Crawl Configuration:")
    print(f"  Mode: {mode.upper()}")
    print(f"  Threads: {max_threads}")
    print(f"  Delay: {delay}s")
    print(f"  Max Depth: {max_depth}")
    print(f"  Respect Robots: {'Yes' if respect_robots else 'No'}")
    print()
    
    # Process queue
    completed = []
    failed = []
    domain_times = []
    
    for domain in domains[:]:  # Copy to avoid modification during iteration
        domain_start = time.time()
        
        success = crawl_domain(domain, mode, max_threads, delay, max_depth, respect_robots)
        domain_time = time.time() - domain_start
        domain_times.append(domain_time)
        
        if success:
            completed.append((domain, domain_time))
            domains.remove(domain)
            print(f"  [+] {domain} ({domain_time:.1f}s)")
        else:
            failed.append((domain, domain_time))
            print(f"  [-] {domain} ({domain_time:.1f}s)")
        
        # Save progress
        save_queue(domains, queue_file)
    
    total_time = time.time() - start_time
    
    # Final report
    print(f"\n{'='*60}")
    print(f"[+] Batch Crawl Complete!")
    print(f"{'='*60}")
    print(f"[*] Total Time: {total_time:.2f} seconds")
    
    if completed:
        avg_time = sum(t for _, t in completed) / len(completed)
        print(f"[+] Successfully crawled: {len(completed)} domains")
        print(f"    Average time per domain: {avg_time:.2f} seconds")
        print(f"    Fastest: {min(t for _, t in completed):.2f}s")
        print(f"    Slowest: {max(t for _, t in completed):.2f}s")
    
    if failed:
        print(f"[-] Failed to crawl: {len(failed)} domains")
        for domain, time_taken in failed:
            print(f"    {domain} ({time_taken:.2f}s)")
    
    if domains:
        print(f"[!] Remaining in queue: {len(domains)} domains")
    
    print(f"\n[+] Results saved to output/ directory")
    print(f"[+] Queue updated in {queue_file}")


def add_to_queue(domains_to_add, queue_file="crawl_queue.txt"):
    """Add domains to the queue"""
    existing = load_queue(queue_file)
    
    added = []
    for domain in domains_to_add:
        domain = domain.strip()
        if domain and domain not in existing:
            existing.append(domain)
            added.append(domain)
    
    if added:
        save_queue(existing, queue_file)
        print(f"[+] Added {len(added)} domains to queue:")
        for domain in added:
            print(f"  + {domain}")
    else:
        print("[!] No new domains to add")


def show_queue(queue_file="crawl_queue.txt"):
    """Display current queue"""
    domains = load_queue(queue_file)
    
    if not domains:
        print("[!] Queue is empty")
        return
    
    print(f"[*] Crawl Queue ({len(domains)} domains):")
    for i, domain in enumerate(domains, 1):
        print(f"  {i}. {domain}")


def main():
    """Batch mode main function"""
    parser = argparse.ArgumentParser(
        description="Batch Web Crawler - Process multiple sites from queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  crawlier -b                               # Process queue
  crawlier -b --add example.com example2.com  # Add domains
  crawlier -b --show                        # Show queue
  crawlier -b --mode mobile --threads 10    # Batch with options
        """
    )
    
    parser.add_argument('--process', action='store_true', default=False,
                       help='Process the queue (default if no other options)')
    parser.add_argument('--add', nargs='+', metavar='DOMAIN',
                       help='Add domains to queue')
    parser.add_argument('--show', action='store_true',
                       help='Show current queue')
    parser.add_argument('-m', '--mode', choices=['mobile', 'pc'], default='pc',
                       help='Crawler mode')
    parser.add_argument('-t', '--threads', type=int, default=5,
                       help='Max threads')
    parser.add_argument('--delay', type=float, default=1.0,
                       help='Delay between requests')
    parser.add_argument('--depth', type=int, default=2,
                       help='Max crawl depth')
    parser.add_argument('--no-robots', action='store_true',
                       help='Ignore robots.txt')
    parser.add_argument('--queue', default='crawl_queue.txt',
                       help='Queue file')
    
    args = parser.parse_args()
    
    try:
        if args.add:
            add_to_queue(args.add, args.queue)
        elif args.show:
            show_queue(args.queue)
        else:
            # Default: process queue
            process_queue(
                queue_file=args.queue,
                mode=args.mode,
                max_threads=args.threads,
                delay=args.delay,
                max_depth=args.depth,
                respect_robots=not args.no_robots
            )
    
    except KeyboardInterrupt:
        print("\n[!] Batch crawl interrupted by user")
    except Exception as e:
        print(f"\n[-] Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
