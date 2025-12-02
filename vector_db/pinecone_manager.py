"""
Pinecone Vector Database Manager for storing and retrieving embeddings
"""
import os
from typing import List, Dict, Any, Optional
import numpy as np
from pinecone import Pinecone, ServerlessSpec
from datetime import datetime


class PineconeManager:
    """Manager for Pinecone vector database with prefix-based indexing"""
    
    def __init__(
        self,
        api_key: str,
        dimension: int = 384,
        similarity_metric: str = "cosine",
        environment: str = "us-east-1"
    ):
        """
        Initialize Pinecone manager
        
        Args:
            api_key: Pinecone API key
            dimension: Embedding dimension (384 for sentence-transformers)
            similarity_metric: "cosine" or "euclidean"
            environment: Pinecone environment/region
        """
        self.api_key = api_key
        self.dimension = dimension
        self.similarity_metric = similarity_metric
        self.environment = environment
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=api_key)
        
        # Store index references
        self.indexes: Dict[str, Any] = {}
    
    def create_index(self, prefix: str, force: bool = False) -> bool:
        """
        Create or get Pinecone index
        
        Args:
            prefix: Index prefix (e.g., "GAP_BP")
            force: If True, delete existing index first
            
        Returns:
            True if successful
        """
        # Pinecone requires lowercase alphanumeric and hyphens only
        index_name = prefix.lower().replace('_', '-')
        
        try:
            # Check if index exists
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if index_name in existing_indexes:
                if force:
                    # Delete existing index
                    self.pc.delete_index(index_name)
                    print(f"Deleted existing index: {index_name}")
                else:
                    # Use existing index
                    self.indexes[prefix] = self.pc.Index(index_name)
                    print(f"Using existing index: {index_name}")
                    return True
            
            # Create new index
            print(f"Creating Pinecone index: {index_name}")
            self.pc.create_index(
                name=index_name,
                dimension=self.dimension,
                metric=self.similarity_metric,
                spec=ServerlessSpec(
                    cloud="aws",
                    region=self.environment
                )
            )
            
            # Wait for index to be ready
            import time
            while index_name not in [idx.name for idx in self.pc.list_indexes()]:
                time.sleep(1)
            
            # Connect to index
            self.indexes[prefix] = self.pc.Index(index_name)
            print(f"Created index: {index_name}")
            return True
            
        except Exception as e:
            print(f"Error creating index {index_name}: {e}")
            return False
    
    def delete_index(self, prefix: str) -> bool:
        """
        Delete Pinecone index
        
        Args:
            prefix: Index prefix
            
        Returns:
            True if successful
        """
        # Pinecone requires lowercase alphanumeric and hyphens only
        index_name = prefix.lower().replace('_', '-')
        
        try:
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            if index_name in existing_indexes:
                self.pc.delete_index(index_name)
                if prefix in self.indexes:
                    del self.indexes[prefix]
                print(f"Deleted index: {index_name}")
                return True
            return False
        except Exception as e:
            print(f"Error deleting index {index_name}: {e}")
            return False
    
    def list_indexes(self) -> List[str]:
        """
        List all available indexes
        
        Returns:
            List of index prefixes (in original format)
        """
        try:
            indexes = self.pc.list_indexes()
            # Convert back to original format (uppercase with underscores)
            result = []
            for idx in indexes:
                if idx.name.startswith('gap-'):
                    # Convert back: gap-bp -> GAP_BP
                    original = idx.name.replace('-', '_').upper()
                    result.append(original)
            return result
        except Exception as e:
            print(f"Error listing indexes: {e}")
            return []
    
    def get_index(self, prefix: str):
        """
        Get index connection
        
        Args:
            prefix: Index prefix
            
        Returns:
            Pinecone index object
        """
        # Pinecone requires lowercase alphanumeric and hyphens only
        index_name = prefix.lower().replace('_', '-')
        
        if prefix not in self.indexes:
            try:
                self.indexes[prefix] = self.pc.Index(index_name)
            except Exception as e:
                print(f"Error connecting to index {index_name}: {e}")
                return None
        
        return self.indexes.get(prefix)
    
    def add_vectors(
        self,
        prefix: str,
        vectors: np.ndarray,
        texts: List[str],
        metadata: List[Dict[str, Any]]
    ) -> bool:
        """
        Add vectors to index
        
        Args:
            prefix: Index prefix
            vectors: Numpy array of vectors
            texts: List of text strings
            metadata: List of metadata dictionaries
            
        Returns:
            True if successful
        """
        index = self.get_index(prefix)
        if not index:
            print(f"Index {prefix} not found")
            return False
        
        try:
            # Prepare vectors for Pinecone
            vectors_to_upsert = []
            for i, (vector, text, meta) in enumerate(zip(vectors, texts, metadata)):
                # Vector IDs must be alphanumeric with hyphens/underscores
                vector_id = f"{prefix.lower().replace('_', '-')}-{i}-{int(datetime.now().timestamp() * 1000)}"
                meta_dict = {
                    "text": text,
                    "prefix": prefix,
                    **meta
                }
                vectors_to_upsert.append({
                    "id": vector_id,
                    "values": vector.tolist(),
                    "metadata": meta_dict
                })
            
            # Upsert in batches of 100
            batch_size = 100
            for i in range(0, len(vectors_to_upsert), batch_size):
                batch = vectors_to_upsert[i:i+batch_size]
                index.upsert(vectors=batch)
            
            print(f"Added {len(vectors_to_upsert)} vectors to {prefix}")
            return True
            
        except Exception as e:
            print(f"Error adding vectors to {prefix}: {e}")
            return False
    
    def search(
        self,
        query_vector: np.ndarray,
        prefix: str,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search in index
        
        Args:
            query_vector: Query vector
            prefix: Index prefix
            k: Number of results
            filter_dict: Optional metadata filter
            
        Returns:
            List of search results
        """
        index = self.get_index(prefix)
        if not index:
            return []
        
        try:
            results = index.query(
                vector=query_vector.tolist(),
                top_k=k,
                include_metadata=True,
                filter=filter_dict
            )
            
            # Format results
            formatted_results = []
            for match in results.matches:
                formatted_results.append({
                    "id": match.id,
                    "score": float(match.score),
                    "metadata": match.metadata or {}
                })
            
            return formatted_results
            
        except Exception as e:
            print(f"Error searching {prefix}: {e}")
            return []
    
    def parallel_search(
        self,
        query_vector: np.ndarray,
        prefixes: List[str],
        k: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search multiple indexes in parallel
        
        Args:
            query_vector: Query vector
            prefixes: List of index prefixes
            k: Number of results per index
            
        Returns:
            Dictionary mapping prefix to results
        """
        from concurrent.futures import ThreadPoolExecutor
        
        results = {}
        
        def search_index(prefix):
            return prefix, self.search(query_vector, prefix, k)
        
        with ThreadPoolExecutor(max_workers=len(prefixes)) as executor:
            futures = [executor.submit(search_index, prefix) for prefix in prefixes]
            for future in futures:
                prefix, result = future.result()
                results[prefix] = result
        
        return results
    
    def get_index_stats(self, prefix: str) -> Dict[str, Any]:
        """
        Get index statistics
        
        Args:
            prefix: Index prefix
            
        Returns:
            Dictionary with stats
        """
        index = self.get_index(prefix)
        if not index:
            return {"vector_count": 0, "dimension": self.dimension}
        
        try:
            stats = index.describe_index_stats()
            return {
                "vector_count": stats.total_vector_count,
                "dimension": self.dimension,
                "index_fullness": stats.index_fullness if hasattr(stats, 'index_fullness') else 0
            }
        except Exception as e:
            print(f"Error getting stats for {prefix}: {e}")
            return {"vector_count": 0, "dimension": self.dimension}

