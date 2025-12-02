"""
Configuration loader for company-specific scraping settings
"""
import json
import os
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """Load and manage company configurations"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize config loader
        
        Args:
            config_path: Path to configuration file. If None, uses default.
        """
        if config_path is None:
            # Default to config directory
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / "config" / "company_config.json"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    def get_company_config(self, company_key: str) -> Dict[str, Any]:
        """
        Get configuration for a specific company
        
        Args:
            company_key: Company identifier (e.g., 'bp')
            
        Returns:
            Company configuration dictionary
        """
        companies = self.config.get("companies", {})
        if company_key not in companies:
            raise ValueError(f"Company '{company_key}' not found in configuration. Available: {list(companies.keys())}")
        
        return companies[company_key]
    
    def get_default_settings(self) -> Dict[str, Any]:
        """Get default scraping settings"""
        return self.config.get("default_settings", {})
    
    def list_companies(self) -> list:
        """List all available companies in configuration"""
        return list(self.config.get("companies", {}).keys())
    
    def get_target_urls(self, company_key: str) -> Dict[str, str]:
        """Get target URLs for a company"""
        company_config = self.get_company_config(company_key)
        return company_config.get("target_urls", {})
    
    def get_search_keywords(self, company_key: str) -> list:
        """Get search keywords for a company"""
        company_config = self.get_company_config(company_key)
        return company_config.get("search_keywords", [])
    
    def get_data_point_config(self, company_key: str, data_point: str) -> Dict[str, Any]:
        """Get configuration for a specific data point"""
        company_config = self.get_company_config(company_key)
        data_points = company_config.get("data_points", {})
        return data_points.get(data_point, {})
    
    def get_document_types(self, company_key: str) -> list:
        """Get document types to download for a company"""
        company_config = self.get_company_config(company_key)
        return company_config.get("document_types", [".pdf", ".docx", ".xlsx"])

