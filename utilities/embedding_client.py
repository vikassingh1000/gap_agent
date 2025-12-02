"""
Embedding client using sentence-transformers (free, local)
"""
from typing import List
import numpy as np


class EmbeddingClient:
    """Client for generating embeddings using sentence-transformers"""
    
    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        """
        Initialize embedding client
        
        Args:
            model_name: Sentence-transformers model name
                - "all-MiniLM-L6-v2" (384 dim, fast, good quality)
                - "all-mpnet-base-v2" (768 dim, better quality, slower)
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the sentence-transformers model"""
        try:
            from sentence_transformers import SentenceTransformer
            print(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print(f"✓ Model loaded successfully")
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
        except Exception as e:
            raise Exception(f"Error loading embedding model: {e}")
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector
        """
        if not self.model:
            self._load_model()
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        if not self.model:
            self._load_model()
        
        # Batch processing for efficiency
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 50,
            batch_size=32
        )
        
        return embeddings.tolist()
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension"""
        if self.model_name == "all-MiniLM-L6-v2":
            return 384
        elif self.model_name == "all-mpnet-base-v2":
            return 768
        else:
            # Try to get from model
            if self.model:
                return self.model.get_sentence_embedding_dimension()
            return 384  # Default

