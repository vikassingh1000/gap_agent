"""
Web scraper package for gap assessment tool
"""
from .browser_scraper import BrowserScraper
from .fallback_scraper import FallbackScraper
from .config_loader import ConfigLoader
from .data_extractor import DataExtractor
from .document_downloader import DocumentDownloader
from .document_parser import DocumentParser

__all__ = [
    'BrowserScraper',
    'FallbackScraper',
    'ConfigLoader',
    'DataExtractor',
    'DocumentDownloader',
    'DocumentParser'
]

