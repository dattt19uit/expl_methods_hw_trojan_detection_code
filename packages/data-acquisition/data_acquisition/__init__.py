"""
data_acquisition - Trust-Hub Circuit Downloader

Python implementation for downloading hardware trojan benchmarks from Trust-Hub.
Downloads circuits from Trust-Hub dynamically (no cached HTML file).
"""

from .downloader import download_circuits, TrustHubDownloader

__version__ = "1.0.0"
__author__ = "Paul Whitten, Francis Wolff, Chris Papachristou"
__all__ = ['download_circuits', 'TrustHubDownloader']
