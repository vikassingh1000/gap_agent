"""
Fallback scraper using requests + BeautifulSoup when browser-use is not available
"""
import time
import json
import requests
from typing import Dict, List, Any, Optional
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

from .config_loader import ConfigLoader
from .data_extractor import DataExtractor
from .document_downloader import DocumentDownloader


class FallbackScraper:
    """Fallback scraper using requests + BeautifulSoup"""
    
    def __init__(self, company_key: str, config_path: Optional[str] = None):
        """
        Initialize fallback scraper
        
        Args:
            company_key: Company identifier (e.g., 'bp')
            config_path: Path to configuration file
        """
        self.config_loader = ConfigLoader(config_path)
        self.company_config = self.config_loader.get_company_config(company_key)
        self.default_settings = self.config_loader.get_default_settings()
        
        self.company_key = company_key
        self.company_name = self.company_config.get("name", company_key)
        
        # Initialize components
        self.data_extractor = DataExtractor(self.company_config)
        download_dir = self.company_config.get("download_directory", f"downloads/{company_key}")
        self.document_downloader = DocumentDownloader(
            download_dir,
            delay=self.default_settings.get("delay_between_requests", 2.0)
        )
        
        # Storage for extracted data
        self.extracted_data: List[Dict[str, Any]] = []
        self.visited_urls: set = set()
        
        # Session for requests
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.default_settings.get('user_agent', 'Mozilla/5.0')
        })
    
    def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape a single URL and extract data
        
        Args:
            url: URL to scrape
            
        Returns:
            Dictionary with extracted data
        """
        if url in self.visited_urls:
            return {}
        
        print(f"Scraping: {url}")
        self.visited_urls.add(url)
        
        try:
            # Fetch page
            response = self.session.get(url, timeout=self.default_settings.get('timeout', 30))
            response.raise_for_status()
            html_content = response.text
            
            # Extract data points
            extracted = self.data_extractor.extract_all_data_points(html_content, url)
            
            # Find and download documents
            document_types = self.config_loader.get_document_types(self.company_key)
            document_links = self.document_downloader.find_document_links(
                html_content, url, document_types
            )
            
            if document_links:
                print(f"Found {len(document_links)} documents to download")
                download_results = self.document_downloader.download_documents(document_links)
                extracted['downloaded_documents'] = download_results
            
            # Add metadata
            extracted['scraped_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
            extracted['company'] = self.company_name
            
            self.extracted_data.append(extracted)
            
            # Delay between requests
            delay = self.default_settings.get("delay_between_requests", 2.0)
            if delay > 0:
                time.sleep(delay)
            
            return extracted
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return {
                'source_url': url,
                'error': str(e),
                'scraped_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
    
    def scrape_all_targets(self) -> List[Dict[str, Any]]:
        """
        Scrape all target URLs for the company
        
        Returns:
            List of extracted data dictionaries
        """
        target_urls = self.config_loader.get_target_urls(self.company_key)
        results = []
        
        print(f"\nStarting scrape for {self.company_name}")
        print(f"Target URLs: {len(target_urls)}")
        
        for url_name, url in target_urls.items():
            print(f"\n--- Scraping {url_name}: {url} ---")
            result = self.scrape_url(url)
            if result:
                results.append(result)
        
        return results
    
    def save_extracted_data(self, output_file: Optional[str] = None) -> str:
        """
        Save all extracted data to JSON file
        
        Args:
            output_file: Output file path. If None, uses default.
            
        Returns:
            Path to saved file
        """
        if output_file is None:
            output_file = f"extracted_data_{self.company_key}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        
        output_path = Path(output_file)
        
        output_data = {
            'company': self.company_name,
            'company_key': self.company_key,
            'extraction_date': time.strftime("%Y-%m-%d %H:%M:%S"),
            'total_pages_scraped': len(self.extracted_data),
            'data': self.extracted_data,
            'download_summary': self.document_downloader.get_download_summary()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\nExtracted data saved to: {output_path}")
        return str(output_path)
    
    def close(self):
        """Cleanup"""
        self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

