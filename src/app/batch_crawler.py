#!/usr/bin/env python3
"""
Batch Crawler - Process multiple sites from queue
"""
import os
import time
from advanced_crawler import Crawlier
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import argparse

console = Console()

def load_queue(queue_file="crawl_queue.txt"):
    """Load domains from queue file"""
    if not os.path.exists(queue_file):
        console.print(f"[yellow]⚠️  Queue file {queue_file} not found. Creating empty queue.[/yellow]")
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
    console.print(f"[blue]🕷️ Starting crawl for: {domain}[/blue]")
    
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
        crawler.save_results(f"output/crawl_results_{domain.replace('.', '_')}.json")
        crawler.close()
        
        console.print(f"[green]✅ Completed crawl for: {domain}[/green]")
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Failed to crawl {domain}: {e}[/red]")
        return False

def process_queue(queue_file="crawl_queue.txt", mode="pc", max_threads=5, delay=1, max_depth=2, respect_robots=True):
    """Process all domains in the queue"""
    domains = load_queue(queue_file)
    
    if not domains:
        console.print("[yellow]📭 Queue is empty. Add domains to crawl_queue.txt[/yellow]")
        return
    
    start_time = time.time()
    
    console.print(f"[cyan]📋 Found {len(domains)} domains in queue:[/cyan]")
    for i, domain in enumerate(domains, 1):
        console.print(f"  {i}. {domain}")
    
    console.print(f"\n[blue]⚙️  Crawl Configuration:[/blue]")
    console.print(f"  Mode: {mode.upper()}")
    console.print(f"  Threads: {max_threads}")
    console.print(f"  Delay: {delay}s")
    console.print(f"  Max Depth: {max_depth}")
    console.print(f"  Respect Robots: {'Yes' if respect_robots else 'No'}")
    console.print()
    
    # Process queue
    completed = []
    failed = []
    domain_times = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
    ) as progress:
        
        main_task = progress.add_task("Processing queue...", total=len(domains))
        
        for domain in domains[:]:  # Copy to avoid modification during iteration
            domain_start = time.time()
            progress.update(main_task, description=f"Crawling {domain}")
            
            success = crawl_domain(domain, mode, max_threads, delay, max_depth, respect_robots)
            domain_time = time.time() - domain_start
            domain_times.append(domain_time)
            
            if success:
                completed.append((domain, domain_time))
                domains.remove(domain)
                progress.update(main_task, description=f"✅ {domain} ({domain_time:.1f}s)")
            else:
                failed.append((domain, domain_time))
                progress.update(main_task, description=f"❌ {domain} ({domain_time:.1f}s)")
            
            progress.update(main_task, advance=1)
            
            # Save progress
            save_queue(domains, queue_file)
    
    total_time = time.time() - start_time
    
    # Final report
    console.print("\n[bold green]📊 Batch Crawl Complete![/bold green]")
    console.print(f"[blue]⏱️  Total Time: {total_time:.2f} seconds[/blue]")
    
    if completed:
        avg_time = sum(t for _, t in completed) / len(completed)
        console.print(f"[green]✅ Successfully crawled: {len(completed)} domains[/green]")
        console.print(f"[cyan]   📈 Average time per domain: {avg_time:.2f} seconds[/cyan]")
        console.print(f"[cyan]   🏃 Fastest: {min(t for _, t in completed):.2f}s[/cyan]")
        console.print(f"[cyan]   🐌 Slowest: {max(t for _, t in completed):.2f}s[/cyan]")
        
        # Show top 5 slowest
        slowest = sorted(completed, key=lambda x: x[1], reverse=True)[:5]
        if len(completed) > 5:
            console.print("[yellow]   🐌 Top 5 slowest domains:[/yellow]")
            for domain, time_taken in slowest:
                console.print(f"     {domain}: {time_taken:.2f}s")
    
    if failed:
        console.print(f"[red]❌ Failed to crawl: {len(failed)} domains[/red]")
        for domain, time_taken in failed:
            console.print(f"   ✗ {domain} ({time_taken:.2f}s)")
    
    if domains:
        console.print(f"[yellow]⏳ Remaining in queue: {len(domains)} domains[/yellow]")
    
    console.print(f"\n[blue]📁 Results saved to output/ directory[/blue]")
    console.print(f"[blue]📋 Queue updated in {queue_file}[/blue]")

def add_to_queue(domains, queue_file="crawl_queue.txt"):
    """Add domains to the queue"""
    existing = load_queue(queue_file)
    
    added = []
    for domain in domains:
        domain = domain.strip()
        if domain and domain not in existing:
            existing.append(domain)
            added.append(domain)
    
    if added:
        save_queue(existing, queue_file)
        console.print(f"[green]✅ Added {len(added)} domains to queue:[/green]")
        for domain in added:
            console.print(f"  + {domain}")
    else:
        console.print("[yellow]ℹ️  No new domains to add[/yellow]")

def show_queue(queue_file="crawl_queue.txt"):
    """Display current queue"""
    domains = load_queue(queue_file)
    
    if not domains:
        console.print("[yellow]📭 Queue is empty[/yellow]")
        return
    
    table = Table(title="📋 Crawl Queue", show_header=True, header_style="bold blue")
    table.add_column("#", style="cyan", justify="right")
    table.add_column("Domain", style="white")
    
    for i, domain in enumerate(domains, 1):
        table.add_row(str(i), domain)
    
    console.print(table)

def main():
    parser = argparse.ArgumentParser(
        description="Batch Web Crawler - Process multiple sites from queue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process the queue
  python batch_crawler.py
  
  # Add domains to queue
  python batch_crawler.py --add example.com another.com
  
  # Show current queue
  python batch_crawler.py --show
  
  # Process with custom settings
  python batch_crawler.py --threads 10 --depth 3 --delay 2
  
  # Process without respecting robots.txt
  python batch_crawler.py --no-robots
        """
    )
    
    parser.add_argument('--add', nargs='+', help='Add domains to queue')
    parser.add_argument('--show', action='store_true', help='Show current queue')
    parser.add_argument('--queue-file', default='crawl_queue.txt', help='Queue file path')
    parser.add_argument('-m', '--mode', choices=['pc', 'mobile'], default='pc', help='Crawl mode')
    parser.add_argument('-t', '--threads', type=int, default=5, help='Max threads per domain')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests')
    parser.add_argument('-d', '--depth', type=int, default=2, help='Max crawl depth')
    parser.add_argument('--no-robots', action='store_true', help='Ignore robots.txt rules')
    
    args = parser.parse_args()
    
    if args.add:
        add_to_queue(args.add, args.queue_file)
    elif args.show:
        show_queue(args.queue_file)
    else:
        # Process the queue
        process_queue(
            queue_file=args.queue_file,
            mode=args.mode,
            max_threads=args.threads,
            delay=args.delay,
            max_depth=args.depth,
            respect_robots=not args.no_robots
        )

if __name__ == "__main__":
    main()