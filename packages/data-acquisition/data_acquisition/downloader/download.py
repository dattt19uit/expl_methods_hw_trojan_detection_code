"""
Trust-Hub circuit downloader - Python implementation.

Downloads hardware trojan benchmarks from Trust-Hub.org.
Dynamically fetches the benchmark index page to get current download links.
"""

import re
import os
import sys
import time
import zipfile
import subprocess
import requests
from pathlib import Path
from typing import List, Dict, Set
from urllib.parse import urljoin
from bs4 import BeautifulSoup


class TrustHubDownloader:
    """Download circuits from Trust-Hub.org"""
    
    BASE_URL = "https://trust-hub.org/"
    BENCHMARKS_URL = "https://trust-hub.org/#/benchmarks/chip-level-trojan"
    
    def __init__(self, output_dir: str = "data", verify_ssl: bool = False, html_file: str = None, circuit_filter: list = None):
        """
        Initialize downloader.
        
        Args:
            output_dir: Directory to save downloaded files
            verify_ssl: Whether to verify SSL certificates (False for expired certs)
            html_file: Optional path to pre-saved HTML file with download links
            circuit_filter: Optional list of circuit names to download (e.g., ['RS232-T1000', 's15850-T100'])
                          If provided, only downloads matching these circuit base names
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.verify_ssl = verify_ssl
        self.html_file = html_file
        self.circuit_filter = set(circuit_filter) if circuit_filter else None
        self.session = requests.Session()
        self.session.verify = verify_ssl
        
        # Statistics
        self.downloaded = 0
        self.skipped = 0
        self.failed = 0
        
    def fetch_benchmark_page(self) -> str:
        """
        Fetch the Trust-Hub benchmarks page.
        
        If html_file is provided, reads from that file.
        Otherwise, fetches from the web.
        
        NOTE: Trust-Hub is a JavaScript single-page app, so live fetching
        won't work without a headless browser. Use --html-file option with
        a pre-saved HTML file for now.
        
        Returns:
            HTML content of the page
        """
        if self.html_file:
            print(f"Loading HTML from file: {self.html_file}...")
            try:
                with open(self.html_file, 'r', encoding='utf-8') as f:
                    html = f.read()
                print(f"[OK] Loaded HTML file ({len(html)} bytes)")
                return html
            except FileNotFoundError:
                print(f"[FAIL] HTML file not found: {self.html_file}")
                raise
        else:
            print(f"Fetching benchmark index from {self.BENCHMARKS_URL}...")
            print("NOTE: Trust-Hub is a JavaScript app - for full link extraction,")
            print("      save the rendered page in browser and use --html-file option")
            
            try:
                response = self.session.get(self.BENCHMARKS_URL, timeout=30)
                response.raise_for_status()
                print(f"[OK] Successfully fetched page ({len(response.text)} bytes)")
                return response.text
            except requests.RequestException as e:
                print(f"[FAIL] Error fetching benchmark page: {e}")
                raise
    
    def extract_download_links(self, html: str) -> List[str]:
        """
        Extract download links from HTML.
        
        The page contains links like: /downloads/resource/file.zip
        
        Args:
            html: HTML content
            
        Returns:
            List of download paths (relative to BASE_URL), filtered by circuit_filter if set
        """
        # Pattern matches /downloads/resource/* excluding quotes
        pattern = r'/downloads/resource/[^"\s]+'
        matches = re.findall(pattern, html)
        
        # Deduplicate while preserving order
        seen: Set[str] = set()
        unique_matches = []
        for match in matches:
            if match not in seen:
                seen.add(match)
                unique_matches.append(match)
        
        # Filter by circuit names if filter is set
        if self.circuit_filter:
            filtered = []
            for link in unique_matches:
                # Extract circuit name from path like /downloads/resource/benchmarks/RS232/RS232-T1000.zip
                # We want to match RS232-T1000 against our filter
                filename = link.split('/')[-1]  # Get filename
                # Remove extension and multi-part indicators
                circuit_name = filename.replace('.zip', '').replace('.rar', '')
                circuit_name = re.sub(r'\.part\d+$', '', circuit_name)  # Remove .part01 etc
                
                # Check if any filter matches
                if any(circuit_name.startswith(f) for f in self.circuit_filter):
                    filtered.append(link)
            
            print(f"[OK] Found {len(unique_matches)} unique download links")
            print(f"[OK] Filtered to {len(filtered)} links matching {len(self.circuit_filter)} circuits")
            return filtered
        
        print(f"[OK] Found {len(unique_matches)} unique download links")
        return unique_matches
    
    def download_file(self, path: str, max_retries: int = 3) -> bool:
        """
        Download a single file.
        
        Args:
            path: Download path (relative to BASE_URL)
            max_retries: Maximum retry attempts
            
        Returns:
            True if successful, False otherwise
        """
        filename = os.path.basename(path)
        filepath = self.output_dir / filename
        url = urljoin(self.BASE_URL, path)
        
        # Skip if already exists
        if filepath.exists():
            print(f"  -- Skipping {filename} (already exists)")
            self.skipped += 1
            return True
        
        # Download with retries
        for attempt in range(max_retries):
            try:
                print(f"  v Downloading {filename}...", end=" ", flush=True)
                
                response = self.session.get(
                    url,
                    timeout=60,
                    stream=True
                )
                response.raise_for_status()
                
                # Write file
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                file_size = filepath.stat().st_size
                print(f"[OK] ({file_size:,} bytes)")
                self.downloaded += 1
                return True
                
            except requests.RequestException as e:
                print(f"[FAIL] Error: {e}")
                
                if attempt < max_retries - 1:
                    print(f"  ~ Retrying {filename} (attempt {attempt + 2}/{max_retries})...")
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    print(f"  [FAIL] Failed {filename} after {max_retries} attempts")
                    self.failed += 1
                    return False
        
        return False
    
    def download_all(self, download_links: List[str]) -> Dict[str, int]:
        """
        Download all files.
        
        Args:
            download_links: List of download paths
            
        Returns:
            Statistics dictionary
        """
        total = len(download_links)
        print(f"\n{'='*70}")
        print(f"Starting download of {total} files...")
        print(f"Output directory: {self.output_dir.absolute()}")
        print(f"{'='*70}\n")
        
        start_time = time.time()
        
        for i, link in enumerate(download_links, 1):
            print(f"[{i}/{total}]", end=" ")
            self.download_file(link)
        
        elapsed = time.time() - start_time
        
        return {
            'total': total,
            'downloaded': self.downloaded,
            'skipped': self.skipped,
            'failed': self.failed,
            'elapsed': elapsed
        }
    
    def print_summary(self, stats: Dict[str, int]):
        """Print download summary."""
        print(f"\n{'='*70}")
        print("DOWNLOAD SUMMARY")
        print(f"{'='*70}")
        print(f"Total files found:      {stats['total']}")
        print(f"Successfully downloaded: {stats['downloaded']}")
        print(f"Already had/skipped:    {stats['skipped']}")
        print(f"Failed downloads:       {stats['failed']}")
        print(f"Time taken:             {stats['elapsed']:.1f}s")
        print(f"{'='*70}")
    
    def extract_archives(self) -> Dict[str, int]:
        """
        Extract all downloaded ZIP and RAR archives.
        
        Returns:
            Statistics about extraction
        """
        print(f"\n{'='*70}")
        print("Extracting archives...")
        print(f"{'='*70}\n")
        
        extracted_zip = 0
        extracted_rar = 0
        failed = 0
        
        # Extract ZIP files
        zip_files = list(self.output_dir.glob("*.zip"))
        for zip_path in zip_files:
            try:
                print(f"  Extracting {zip_path.name}...", end=" ")
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(self.output_dir)
                print("[OK]")
                extracted_zip += 1
            except Exception as e:
                print(f"[FAIL] Error: {e}")
                failed += 1
        
        # Extract RAR files (requires unrar command)
        rar_files = list(self.output_dir.glob("*.rar"))
        if rar_files:
            # Check if unrar is available
            try:
                subprocess.run(['unrar'], capture_output=True, check=False)
                has_unrar = True
            except FileNotFoundError:
                print("  WARNING: unrar not found. Skipping RAR extraction.")
                print("  Install with: sudo apt install unrar")
                has_unrar = False
            
            if has_unrar:
                for rar_path in rar_files:
                    try:
                        print(f"  Extracting {rar_path.name}...", end=" ")
                        result = subprocess.run(
                            ['unrar', 'x', '-o+', str(rar_path), str(self.output_dir)],
                            capture_output=True,
                            text=True,
                            check=False
                        )
                        if result.returncode == 0:
                            print("[OK]")
                            extracted_rar += 1
                        else:
                            print(f"[FAIL] Error: {result.stderr}")
                            failed += 1
                    except Exception as e:
                        print(f"[FAIL] Error: {e}")
                        failed += 1
        
        print(f"\n{'='*70}")
        print("EXTRACTION SUMMARY")
        print(f"{'='*70}")
        print(f"ZIP files extracted:  {extracted_zip}")
        print(f"RAR files extracted:  {extracted_rar}")
        print(f"Failed extractions:   {failed}")
        print(f"{'='*70}")
        
        return {
            'zip': extracted_zip,
            'rar': extracted_rar,
            'failed': failed
        }


def download_circuits(output_dir: str = "data", verify_ssl: bool = False, extract: bool = True, html_file: str = None, circuit_filter: list = None) -> Dict[str, int]:
    """
    Download circuits from Trust-Hub.
    
    This is the main entry point for the downloader.
    
    Args:
        output_dir: Directory to save downloaded files
        verify_ssl: Whether to verify SSL certificates
        extract: Whether to extract downloaded archives
        html_file: Optional path to pre-saved HTML with download links
        circuit_filter: Optional list of circuit names to download (e.g., ['RS232-T1000', 's15850-T100'])
        
    Returns:
        Statistics dictionary
        
    Example:
        >>> # Using existing HTML file
        >>> stats = download_circuits(
        ...     output_dir="data/raw",
        ...     html_file="dl_trust_hub/untitled.html",
        ...     extract=True
        ... )
        >>> print(f"Downloaded {stats['downloaded']} files")
    """
    downloader = TrustHubDownloader(
        output_dir=output_dir,
        verify_ssl=verify_ssl,
        html_file=html_file,
        circuit_filter=circuit_filter
    )
    
    # Fetch and parse benchmark page
    html = downloader.fetch_benchmark_page()
    links = downloader.extract_download_links(html)
    
    # Download all files
    stats = downloader.download_all(links)
    downloader.print_summary(stats)
    
    # Extract archives if requested
    if extract:
        extract_stats = downloader.extract_archives()
        stats['extraction'] = extract_stats
    
    return stats


def main():
    """Command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Download hardware trojan benchmarks from Trust-Hub.org"
    )
    parser.add_argument(
        '--output', '-o',
        default='data',
        help='Output directory for downloaded files (default: data)'
    )
    parser.add_argument(
        '--verify-ssl',
        action='store_true',
        help='Verify SSL certificates (default: False, for expired certs)'
    )
    parser.add_argument(
        '--no-extract',
        action='store_true',
        help='Do not extract archives after download'
    )
    parser.add_argument(
        '--html-file',
        help='Path to pre-saved HTML file with download links (for JavaScript-rendered pages)'
    )
    parser.add_argument(
        '--circuits',
        help='Path to circuit config JSON to filter downloads (only downloads circuits in config)'
    )
    
    args = parser.parse_args()
    
    # Load circuit filter if provided
    circuit_filter = None
    if args.circuits:
        import json
        with open(args.circuits, 'r') as f:
            configs = json.load(f)
        # Extract unique circuit base names
        circuits = set()
        for name in configs.keys():
            parts = name.rsplit('-', 1)  # Remove tech suffix (90nm, 180nm)
            base_name = parts[0]
            circuits.add(base_name)
        circuit_filter = list(circuits)
        print(f"Loaded {len(circuit_filter)} circuits from config: {args.circuits}")
    
    try:
        stats = download_circuits(
            output_dir=args.output,
            verify_ssl=args.verify_ssl,
            extract=not args.no_extract,
            html_file=args.html_file,
            circuit_filter=circuit_filter
        )
        
        # Exit with error code if any downloads failed
        sys.exit(0 if stats['failed'] == 0 else 1)
        
    except KeyboardInterrupt:
        print("\n\nDownload interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
