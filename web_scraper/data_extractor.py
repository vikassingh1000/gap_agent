"""
Data extraction logic for specific data points
"""
from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re


class DataExtractor:
    """Extract specific data points from HTML content"""
    
    def __init__(self, company_config: Dict[str, Any]):
        """
        Initialize data extractor
        
        Args:
            company_config: Company configuration dictionary
        """
        self.company_config = company_config
        self.data_points_config = company_config.get("data_points", {})
        self.search_keywords = company_config.get("search_keywords", [])
    
    def extract_all_data_points(self, html_content: str, url: str = "") -> Dict[str, Any]:
        """
        Extract all configured data points from HTML content
        
        Args:
            html_content: HTML content as string
            url: Source URL (for reference)
            
        Returns:
            Dictionary with all extracted data points
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        extracted_data = {
            'source_url': url,
            'strategic_pillars': self._extract_strategic_pillars(soup),
            'technology_investment': self._extract_technology_investment(soup),
            'compliance_frameworks': self._extract_compliance_frameworks(soup),
            'digitization_goals': self._extract_digitization_goals(soup),
            'risk_management': self._extract_risk_management(soup),
            'data_governance': self._extract_data_governance(soup),
            'audit_controls': self._extract_audit_controls(soup),
            'raw_text_snippets': self._extract_relevant_snippets(soup)
        }
        
        return extracted_data
    
    def _extract_by_config(self, soup: BeautifulSoup, data_point_key: str) -> List[str]:
        """Generic extraction method using configuration"""
        config = self.data_points_config.get(data_point_key, {})
        selectors = config.get("selectors", ["p", "div", "section"])
        keywords = config.get("keywords", [])
        
        extracted = []
        
        # Find elements matching selectors
        for selector in selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if text and len(text) > 20:  # Filter out very short texts
                    # Check if text contains any keywords
                    text_lower = text.lower()
                    if any(keyword.lower() in text_lower for keyword in keywords):
                        if text not in extracted:  # Avoid duplicates
                            extracted.append(text)
        
        return extracted[:50]  # Limit to 50 items per category
    
    def _extract_strategic_pillars(self, soup: BeautifulSoup) -> List[str]:
        """Extract strategic pillars and initiatives"""
        return self._extract_by_config(soup, "strategic_pillars")
    
    def _extract_technology_investment(self, soup: BeautifulSoup) -> List[str]:
        """Extract technology investment areas"""
        return self._extract_by_config(soup, "technology_investment")
    
    def _extract_compliance_frameworks(self, soup: BeautifulSoup) -> List[str]:
        """Extract compliance frameworks"""
        return self._extract_by_config(soup, "compliance_frameworks")
    
    def _extract_digitization_goals(self, soup: BeautifulSoup) -> List[str]:
        """Extract digitization goals and targets"""
        return self._extract_by_config(soup, "digitization_goals")
    
    def _extract_risk_management(self, soup: BeautifulSoup) -> List[str]:
        """Extract risk management approaches"""
        return self._extract_by_config(soup, "risk_management")
    
    def _extract_data_governance(self, soup: BeautifulSoup) -> List[str]:
        """Extract data governance statements"""
        return self._extract_by_config(soup, "data_governance")
    
    def _extract_audit_controls(self, soup: BeautifulSoup) -> List[str]:
        """Extract audit and controls references"""
        return self._extract_by_config(soup, "audit_controls")
    
    def _extract_relevant_snippets(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """
        Extract relevant text snippets containing search keywords
        
        Returns:
            List of dictionaries with 'text' and 'context'
        """
        snippets = []
        all_text_elements = soup.find_all(['p', 'div', 'section', 'article', 'li'])
        
        for element in all_text_elements:
            text = element.get_text(strip=True)
            if not text or len(text) < 50:  # Skip very short texts
                continue
            
            text_lower = text.lower()
            
            # Check if text contains any search keywords
            matched_keywords = [
                keyword for keyword in self.search_keywords
                if keyword.lower() in text_lower
            ]
            
            if matched_keywords:
                # Get context (parent heading or section)
                context = ""
                parent = element.find_parent(['section', 'article', 'div'])
                if parent:
                    heading = parent.find(['h1', 'h2', 'h3', 'h4', 'h5'])
                    if heading:
                        context = heading.get_text(strip=True)
                
                snippets.append({
                    'text': text[:500],  # Limit snippet length
                    'context': context,
                    'matched_keywords': matched_keywords,
                    'element_type': element.name
                })
        
        return snippets[:100]  # Limit to 100 snippets
    
    def extract_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract data points from plain text (for document parsing)
        
        Args:
            text: Plain text content
            
        Returns:
            Dictionary with extracted data points
        """
        extracted = {
            'strategic_pillars': [],
            'technology_investment': [],
            'compliance_frameworks': [],
            'digitization_goals': [],
            'risk_management': [],
            'data_governance': [],
            'audit_controls': []
        }
        
        text_lower = text.lower()
        
        # Extract paragraphs/sentences containing keywords
        sentences = re.split(r'[.!?]\s+', text)
        
        for data_point, config in self.data_points_config.items():
            keywords = config.get("keywords", [])
            for sentence in sentences:
                sentence_lower = sentence.lower()
                if any(keyword.lower() in sentence_lower for keyword in keywords):
                    if len(sentence.strip()) > 20:
                        extracted[data_point].append(sentence.strip())
        
        # Deduplicate and limit
        for key in extracted:
            extracted[key] = list(set(extracted[key]))[:50]
        
        return extracted

