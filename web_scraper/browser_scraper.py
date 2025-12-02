"""
Browser-use based web scraper for intelligent web scraping
"""
import os
import time
import json
from typing import Dict, List, Any, Optional
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    from browser_use import Browser, Agent
    try:
        from browser_use.browser.browser import BrowserConfig
    except ImportError:
        # Try alternative import path
        BrowserConfig = None
    BROWSER_USE_AVAILABLE = True
except ImportError:
    BROWSER_USE_AVAILABLE = False
    Browser = None
    Agent = None
    BrowserConfig = None
    print("Warning: browser-use not installed. Install with: pip install browser-use")

from .config_loader import ConfigLoader
from .data_extractor import DataExtractor
from .document_downloader import DocumentDownloader


class BrowserScraper:
    """Intelligent web scraper using browser-use"""
    
    def __init__(self, company_key: str, config_path: Optional[str] = None, agent_config: Optional[Dict[str, Any]] = None):
        """
        Initialize browser scraper
        
        Args:
            company_key: Company identifier (e.g., 'bp')
            config_path: Path to configuration file
            agent_config: Optional agent configuration (for browser-use API key)
        """
        if not BROWSER_USE_AVAILABLE:
            raise ImportError("browser-use library is required. Install with: pip install browser-use")
        
        self.config_loader = ConfigLoader(config_path)
        self.company_config = self.config_loader.get_company_config(company_key)
        self.default_settings = self.config_loader.get_default_settings()
        
        # Set browser-use API key if provided in agent config
        if agent_config:
            browser_api_key = agent_config.get("extraction", {}).get("browser_use_api_key")
            if browser_api_key:
                os.environ["BROWSER_USE_API_KEY"] = browser_api_key
        
        self.company_key = company_key
        self.company_name = self.company_config.get("name", company_key)
        
        # Initialize components
        self.data_extractor = DataExtractor(self.company_config)
        download_dir = self.company_config.get("download_directory", f"downloads/{company_key}")
        self.document_downloader = DocumentDownloader(
            download_dir,
            delay=self.default_settings.get("delay_between_requests", 2.0)
        )
        
        # Initialize browser
        self.browser = None
        self.agent = None
        
        # Storage for extracted data
        self.extracted_data: List[Dict[str, Any]] = []
        self.visited_urls: set = set()
    
    def initialize_browser(self):
        """Initialize browser and agent"""
        try:
            if BrowserConfig is not None:
                browser_config = BrowserConfig(
                    headless=True,  # Set to False for debugging
                    disable_security=True
                )
                self.browser = Browser(config=browser_config)
            else:
                # Use default browser config
                self.browser = Browser()
            
            self.agent = Agent(
                task="Navigate and extract data from company websites",
                browser=self.browser
            )
            print("Browser initialized successfully")
        except Exception as e:
            print(f"Error initializing browser: {e}")
            print("Note: You may need to install Playwright browsers: playwright install chromium")
            raise
    
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
            # For now, use fallback method (requests) as browser-use async is complex
            # TODO: Implement proper async handling for browser-use
            import requests
            headers = {'User-Agent': self.default_settings.get('user_agent', 'Mozilla/5.0')}
            response = requests.get(url, headers=headers, timeout=30)
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
        if self.browser is None:
            self.initialize_browser()
        
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
    
    def search_and_scrape(self, search_query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for relevant pages and scrape them
        
        Args:
            search_query: Search query
            max_results: Maximum number of results to scrape
            
        Returns:
            List of extracted data dictionaries
        """
        if self.browser is None:
            self.initialize_browser()
        
        try:
            # Use browser-use agent to search
            search_prompt = f"""
            Search for: {search_query} on {self.company_config.get('base_url')}
            Find pages related to: {', '.join(self.config_loader.get_search_keywords(self.company_key)[:5])}
            Return up to {max_results} relevant URLs
            """
            
            result = self.agent.run(search_prompt)
            
            # Extract URLs from result (this would need to be adapted based on browser-use's response format)
            # For now, we'll use a simpler approach
            print(f"Search completed. Scraping relevant pages...")
            
            # You would parse the result to get URLs and then scrape them
            # This is a placeholder - actual implementation depends on browser-use's response format
            
        except Exception as e:
            print(f"Error in search and scrape: {e}")
        
        return []
    
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
        """Close browser and cleanup"""
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

