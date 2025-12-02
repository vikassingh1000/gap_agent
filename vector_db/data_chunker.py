"""
Data chunker using LangChain TokenTextSplitter with size limits
"""
import os
from typing import List, Dict, Any
from langchain_text_splitters import TokenTextSplitter


class DataChunker:
    """Chunk text data using TokenTextSplitter with size limits"""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        encoding_name: str = "gpt2",
        max_size_mb: float = 20.0
    ):
        """
        Initialize data chunker
        
        Args:
            chunk_size: Number of tokens per chunk
            chunk_overlap: Number of tokens to overlap between chunks
            encoding_name: Token encoding name (default: gpt2)
            max_size_mb: Maximum size in MB per source
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
        
        # Initialize TokenTextSplitter
        self.splitter = TokenTextSplitter(
            encoding_name=encoding_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
    
    def chunk_text(self, text: str, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Chunk text into smaller pieces
        
        Args:
            text: Input text to chunk
            metadata: Optional metadata to attach to chunks
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        # Check size limit
        text_size = len(text.encode('utf-8'))
        if text_size > self.max_size_bytes:
            # Truncate text if too large
            max_chars = int(self.max_size_bytes * 0.9)  # Leave some buffer
            text = text[:max_chars]
            print(f"Warning: Text truncated to {max_chars} characters (max {self.max_size_bytes} bytes)")
        
        # Split text
        chunks = self.splitter.split_text(text)
        
        # Create chunk dictionaries
        chunk_list = []
        for i, chunk in enumerate(chunks):
            chunk_dict = {
                "text": chunk,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "metadata": metadata or {}
            }
            chunk_list.append(chunk_dict)
        
        return chunk_list
    
    def chunk_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Chunk multiple documents
        
        Args:
            documents: List of document dictionaries with 'text' and optional 'metadata'
            
        Returns:
            List of all chunks from all documents
        """
        all_chunks = []
        total_size = 0
        
        for doc_idx, doc in enumerate(documents):
            text = doc.get("text", "")
            metadata = doc.get("metadata", {})
            metadata["document_index"] = doc_idx
            
            # Check cumulative size
            text_size = len(text.encode('utf-8'))
            if total_size + text_size > self.max_size_bytes:
                print(f"Warning: Reached size limit. Skipping remaining documents.")
                break
            
            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
            total_size += text_size
        
        return all_chunks
    
    def chunk_extracted_data(self, extracted_data: Dict[str, Any], source: str) -> List[Dict[str, Any]]:
        """
        Chunk extracted data from scraper
        
        Args:
            extracted_data: Dictionary with extracted data points
            source: Source identifier (e.g., "bp", "kpmg")
            
        Returns:
            List of chunks with metadata
        """
        all_chunks = []
        
        # Combine all text fields
        text_parts = []
        
        # Add strategic pillars
        for item in extracted_data.get("strategic_pillars", []):
            text_parts.append(f"Strategic Pillar: {item}")
        
        # Add technology investment
        for item in extracted_data.get("technology_investment", []):
            text_parts.append(f"Technology Investment: {item}")
        
        # Add compliance frameworks
        for item in extracted_data.get("compliance_frameworks", []):
            text_parts.append(f"Compliance Framework: {item}")
        
        # Add digitization goals
        for item in extracted_data.get("digitization_goals", []):
            text_parts.append(f"Digitization Goal: {item}")
        
        # Add risk management
        for item in extracted_data.get("risk_management", []):
            text_parts.append(f"Risk Management: {item}")
        
        # Add data governance
        for item in extracted_data.get("data_governance", []):
            text_parts.append(f"Data Governance: {item}")
        
        # Add audit controls
        for item in extracted_data.get("audit_controls", []):
            text_parts.append(f"Audit & Controls: {item}")
        
        # Add raw text snippets
        for snippet in extracted_data.get("raw_text_snippets", []):
            text_parts.append(snippet.get("text", ""))
        
        # Combine all text
        combined_text = "\n\n".join(text_parts)
        
        # Create metadata
        metadata = {
            "source": source,
            "source_url": extracted_data.get("source_url", ""),
            "scraped_at": extracted_data.get("scraped_at", ""),
            "data_type": "extracted_web_data"
        }
        
        # Chunk the combined text
        chunks = self.chunk_text(combined_text, metadata)
        
        return chunks

