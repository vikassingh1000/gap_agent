"""
Extraction Tool for Gap Assessment Agent
Extracts data from company websites and stores in vector DB
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from web_scraper import BrowserScraper, FallbackScraper, DocumentParser
from web_scraper.config_loader import ConfigLoader
from vector_db.pinecone_manager import PineconeManager
from vector_db.data_chunker import DataChunker
from utilities.embedding_client import EmbeddingClient


class ExtractionTool:
    """Tool for extracting and storing company data"""
    
    def __init__(
        self,
        agent_config: Dict[str, Any],
        embedding_client: EmbeddingClient,
        company_config_path: Optional[str] = None
    ):
        """
        Initialize extraction tool
        
        Args:
            agent_config: Agent configuration dictionary
            embedding_client: Embedding client instance
            company_config_path: Path to company configuration file
        """
        self.agent_config = agent_config
        self.extraction_config = agent_config.get("extraction", {})
        self.vector_db_config = agent_config.get("vector_db", {})
        
        # Initialize components
        self.config_loader = ConfigLoader(company_config_path)
        
        # Initialize vector DB (Pinecone)
        if self.vector_db_config.get("type") != "pinecone":
            raise ValueError("Pinecone is required. Update config to use Pinecone.")
        
        self.vector_db = PineconeManager(
            api_key=self.vector_db_config["api_key"],
            dimension=self.vector_db_config.get("dimension", 768),
            similarity_metric=self.vector_db_config.get("similarity_metric", "cosine"),
            environment=self.vector_db_config.get("environment", "us-east-1")
        )
        
        self.chunker = DataChunker(
            chunk_size=self.extraction_config.get("chunk_size", 1000),
            chunk_overlap=self.extraction_config.get("chunk_overlap", 200),
            encoding_name=self.extraction_config.get("token_encoding", "gpt2"),
            max_size_mb=self.extraction_config.get("max_data_size_mb_per_source", 20.0)
        )
        
        # Use provided embedding client
        self.embedding_client = embedding_client
        
        # Date tracking file
        self.date_tracking_file = Path("config/extraction_dates.json")
        self._load_extraction_dates()
    
    def _load_extraction_dates(self):
        """Load last extraction dates"""
        if self.date_tracking_file.exists():
            with open(self.date_tracking_file, 'r') as f:
                self.extraction_dates = json.load(f)
        else:
            self.extraction_dates = {}
    
    def _save_extraction_dates(self):
        """Save last extraction dates"""
        self.date_tracking_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.date_tracking_file, 'w') as f:
            json.dump(self.extraction_dates, f, indent=2)
    
    def _should_extract(self, company_key: str, force: bool = False) -> bool:
        """
        Check if extraction should be performed
        
        Args:
            company_key: Company identifier
            force: Force extraction regardless of date or config
            
        Returns:
            True if extraction should be performed
        """
        # If force is explicitly True, always extract
        if force:
            return True
        
        # Check force_refresh config - if False, never extract (skip date check)
        force_refresh = self.extraction_config.get("force_refresh", False)
        if not force_refresh:
            return False
        
        # If no previous extraction, extract
        if company_key not in self.extraction_dates:
            return True
        
        # Check if 14 days have passed
        last_extraction = datetime.fromisoformat(self.extraction_dates[company_key])
        days_since = (datetime.now() - last_extraction).days
        interval_days = self.extraction_config.get("biweekly_interval_days", 14)
        
        return days_since >= interval_days
    
    def extract_company_data(
        self,
        company_key: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Extract data for a company and store in vector DB
        
        Args:
            company_key: Company identifier (e.g., "bp", "kpmg")
            force: Force extraction even if recent
            
        Returns:
            Dictionary with extraction results
        """
        prefix = f"GAP_{company_key.upper()}"
        
        # Check if extraction needed
        if not self._should_extract(company_key, force):
            force_refresh = self.extraction_config.get("force_refresh", False)
            if not force_refresh:
                reason = "force_refresh is False in config. Extraction disabled."
            else:
                reason = "Recent extraction exists. Use force=True to re-extract."
            
            return {
                "status": "skipped",
                "reason": reason,
                "last_extraction": self.extraction_dates.get(company_key),
                "prefix": prefix,
                "force_refresh": force_refresh
            }
        
        # Force refresh if requested (delete and recreate index)
        if force:
            self.vector_db.delete_index(prefix)
            self.vector_db.create_index(prefix, force=True)
        
        print(f"Extracting data for {company_key}...")
        
        try:
            # Initialize scraper (pass agent_config for browser-use API key)
            try:
                scraper = BrowserScraper(company_key, agent_config=self.agent_config)
            except (ImportError, Exception) as e:
                print(f"Browser-use not available, using fallback: {e}")
                scraper = FallbackScraper(company_key)
            
            # Scrape all target URLs
            results = scraper.scrape_all_targets()
            
            # Parse documents if available
            parser = DocumentParser()
            download_dir = scraper.company_config.get("download_directory", f"downloads/{company_key}")
            parsed_docs = parser.parse_directory(download_dir)
            
            # Combine all extracted data
            all_chunks = []
            
            # Chunk web-scraped data
            for result in results:
                if "error" not in result:
                    chunks = self.chunker.chunk_extracted_data(result, company_key)
                    all_chunks.extend(chunks)
            
            # Chunk parsed documents
            for doc in parsed_docs:
                if doc.get("status") == "success" and "text" in doc:
                    doc_chunks = self.chunker.chunk_text(
                        doc["text"],
                        {
                            "source": company_key,
                            "file_path": doc.get("file_path", ""),
                            "file_type": doc.get("file_type", ""),
                            "data_type": "parsed_document"
                        }
                    )
                    all_chunks.extend(doc_chunks)
            
            if not all_chunks:
                return {
                    "status": "error",
                    "error": "No data extracted",
                    "prefix": prefix
                }
            
            # Generate embeddings using sentence-transformers (no quota limits!)
            print(f"Generating embeddings for {len(all_chunks)} chunks...")
            texts = [chunk["text"] for chunk in all_chunks]
            
            try:
                # Generate all embeddings at once (sentence-transformers is local, no quota)
                print(f"  Generating embeddings using sentence-transformers...")
                embeddings = self.embedding_client.embed_documents(texts)
                
                # Convert to numpy array
                import numpy as np
                vectors = np.array(embeddings).astype('float32')
                
                print(f"  ✓ Generated {len(vectors)} embeddings")
                
                # Store in vector DB
                print(f"Storing {len(vectors)} vectors in Pinecone index {prefix}...")
                metadata = [chunk.get("metadata", {}) for chunk in all_chunks]
                success = self.vector_db.add_vectors(prefix, vectors, texts, metadata)
                
                if not success:
                    return {
                        "status": "error",
                        "error": "Failed to store vectors in Pinecone",
                        "prefix": prefix,
                        "chunks_extracted": len(all_chunks)
                    }
                
            except Exception as e:
                return {
                    "status": "error",
                    "error": f"Error generating embeddings: {str(e)}",
                    "prefix": prefix,
                    "chunks_extracted": len(all_chunks)
                }
            
            # Update extraction date
            self.extraction_dates[company_key] = datetime.now().isoformat()
            self._save_extraction_dates()
            
            # Cleanup
            scraper.close()
            
            return {
                "status": "success",
                "prefix": prefix,
                "chunks_stored": len(all_chunks),
                "vectors_stored": len(vectors),
                "extraction_date": self.extraction_dates[company_key]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "prefix": prefix
            }
    
    def extract_all_companies(self, force: bool = False) -> Dict[str, Any]:
        """
        Extract data for all configured companies
        
        Args:
            force: Force extraction for all companies
            
        Returns:
            Dictionary with results for each company
        """
        companies_config = self.agent_config.get("companies", {})
        primary = companies_config.get("primary", "bp")
        benchmarks = companies_config.get("benchmark_companies", [])
        
        all_companies = [primary] + benchmarks
        results = {}
        
        for company_key in all_companies:
            print(f"\n{'='*60}")
            print(f"Processing: {company_key}")
            print(f"{'='*60}")
            results[company_key] = self.extract_company_data(company_key, force=force)
        
        return results
    
    def get_extraction_status(self) -> Dict[str, Any]:
        """Get status of all extractions"""
        companies_config = self.agent_config.get("companies", {})
        primary = companies_config.get("primary", "bp")
        benchmarks = companies_config.get("benchmark_companies", [])
        
        all_companies = [primary] + benchmarks
        status = {}
        
        for company_key in all_companies:
            prefix = f"GAP_{company_key.upper()}"
            stats = self.vector_db.get_index_stats(prefix)
            status[company_key] = {
                "prefix": prefix,
                "last_extraction": self.extraction_dates.get(company_key),
                "index_exists": prefix in self.vector_db.list_indexes(),
                "stats": stats
            }
        
        return status

