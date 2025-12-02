"""
Document downloader for PDF, DOCX, Excel, and other files
"""
import os
import requests
from pathlib import Path
from typing import List, Set
from urllib.parse import urljoin, urlparse
import time


class DocumentDownloader:
    """Download documents from web pages"""
    
    def __init__(self, download_directory: str, delay: float = 2.0):
        """
        Initialize document downloader
        
        Args:
            download_directory: Base directory for downloads
            delay: Delay between downloads in seconds
        """
        self.download_directory = Path(download_directory)
        self.download_directory.mkdir(parents=True, exist_ok=True)
        self.delay = delay
        self.downloaded_files: Set[str] = set()
        self.failed_downloads: List[dict] = []
    
    def find_document_links(self, html_content: str, base_url: str, document_types: List[str]) -> List[dict]:
        """
        Find all document links in HTML content
        
        Args:
            html_content: HTML content as string
            base_url: Base URL for resolving relative links
            document_types: List of file extensions to look for (e.g., ['.pdf', '.docx'])
            
        Returns:
            List of document link dictionaries with 'url' and 'filename'
        """
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        document_links = []
        
        # Find all links
        for link in soup.find_all('a', href=True):
            href = link['href']
            url = urljoin(base_url, href)
            
            # Check if it's a document type we're interested in
            parsed_url = urlparse(url)
            path = parsed_url.path.lower()
            
            for doc_type in document_types:
                if path.endswith(doc_type.lower()):
                    filename = os.path.basename(parsed_url.path) or f"document_{len(document_links)}.{doc_type[1:]}"
                    document_links.append({
                        'url': url,
                        'filename': filename,
                        'type': doc_type,
                        'text': link.get_text(strip=True)
                    })
                    break
        
        return document_links
    
    def download_document(self, url: str, filename: str = None) -> dict:
        """
        Download a single document
        
        Args:
            url: URL of the document
            filename: Optional filename. If None, extracted from URL
            
        Returns:
            Dictionary with download status and file path
        """
        try:
            # Extract filename if not provided
            if filename is None:
                parsed_url = urlparse(url)
                filename = os.path.basename(parsed_url.path) or "document"
            
            # Skip if already downloaded
            if url in self.downloaded_files:
                return {
                    'status': 'skipped',
                    'url': url,
                    'filename': filename,
                    'reason': 'Already downloaded'
                }
            
            # Create file path
            file_path = self.download_directory / filename
            
            # Download file
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=30, stream=True)
            response.raise_for_status()
            
            # Save file
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.downloaded_files.add(url)
            
            return {
                'status': 'success',
                'url': url,
                'filename': filename,
                'file_path': str(file_path),
                'size': file_path.stat().st_size
            }
            
        except Exception as e:
            error_info = {
                'status': 'failed',
                'url': url,
                'filename': filename,
                'error': str(e)
            }
            self.failed_downloads.append(error_info)
            return error_info
    
    def download_documents(self, document_links: List[dict]) -> List[dict]:
        """
        Download multiple documents
        
        Args:
            document_links: List of document link dictionaries
            
        Returns:
            List of download results
        """
        results = []
        
        for doc_link in document_links:
            result = self.download_document(doc_link['url'], doc_link['filename'])
            results.append(result)
            
            # Delay between downloads
            if self.delay > 0:
                time.sleep(self.delay)
        
        return results
    
    def get_download_summary(self) -> dict:
        """Get summary of downloads"""
        return {
            'total_downloaded': len(self.downloaded_files),
            'failed_downloads': len(self.failed_downloads),
            'download_directory': str(self.download_directory),
            'failed': self.failed_downloads
        }

