"""
FAISS Vector Database Manager for storing and retrieving embeddings
"""
import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import faiss
from datetime import datetime


class FaissManager:
    """Manager for FAISS vector database with prefix-based indexing"""
    
    def __init__(
        self,
        index_directory: str = "vector_db_indexes",
        dimension: int = 768,
        similarity_metric: str = "cosine"
    ):
        """
        Initialize FAISS manager
        
        Args:
            index_directory: Directory to store indexes
            dimension: Embedding dimension
            similarity_metric: "cosine" or "l2"
        """
        self.index_directory = Path(index_directory)
        self.index_directory.mkdir(parents=True, exist_ok=True)
        self.dimension = dimension
        self.similarity_metric = similarity_metric
        
        # Store indexes by prefix
        self.indexes: Dict[str, faiss.Index] = {}
        self.metadata: Dict[str, List[Dict[str, Any]]] = {}
        self.index_paths: Dict[str, Path] = {}
        
        # Load existing indexes
        self._load_existing_indexes()
    
    def _load_existing_indexes(self):
        """Load existing indexes from disk"""
        for index_file in self.index_directory.glob("*.index"):
            prefix = index_file.stem.replace("_index", "")
            try:
                index = faiss.read_index(str(index_file))
                self.indexes[prefix] = index
                self.index_paths[prefix] = index_file
                
                # Load metadata
                metadata_file = index_file.with_suffix(".metadata")
                if metadata_file.exists():
                    with open(metadata_file, 'rb') as f:
                        self.metadata[prefix] = pickle.load(f)
                else:
                    self.metadata[prefix] = []
                
                print(f"Loaded index: {prefix} ({index.ntotal} vectors)")
            except Exception as e:
                print(f"Error loading index {index_file}: {e}")
    
    def create_index(self, prefix: str, force: bool = False) -> bool:
        """
        Create a new index with prefix
        
        Args:
            prefix: Index prefix (e.g., "GAP_BP", "GAP_KPMG")
            force: If True, delete existing index and create new
            
        Returns:
            True if created successfully
        """
        index_name = f"{prefix}_index"
        index_path = self.index_directory / f"{index_name}.index"
        
        if force and prefix in self.indexes:
            # Delete existing index
            del self.indexes[prefix]
            if index_path.exists():
                index_path.unlink()
            metadata_path = index_path.with_suffix(".metadata")
            if metadata_path.exists():
                metadata_path.unlink()
        
        if prefix in self.indexes and not force:
            print(f"Index {prefix} already exists. Use force=True to recreate.")
            return False
        
        # Create index based on similarity metric
        if self.similarity_metric == "cosine":
            # For cosine similarity, use IndexFlatIP with normalized vectors
            index = faiss.IndexFlatIP(self.dimension)
        else:
            # For L2 distance
            index = faiss.IndexFlatL2(self.dimension)
        
        self.indexes[prefix] = index
        self.index_paths[prefix] = index_path
        self.metadata[prefix] = []
        
        print(f"Created index: {prefix}")
        return True
    
    def add_vectors(
        self,
        prefix: str,
        vectors: np.ndarray,
        texts: List[str],
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Add vectors to index
        
        Args:
            prefix: Index prefix
            vectors: Numpy array of embeddings (n_vectors, dimension)
            texts: List of text chunks
            metadata: Optional list of metadata dicts
            
        Returns:
            True if successful
        """
        if prefix not in self.indexes:
            self.create_index(prefix)
        
        # Normalize vectors for cosine similarity
        if self.similarity_metric == "cosine":
            faiss.normalize_L2(vectors)
        
        # Add to index
        self.indexes[prefix].add(vectors)
        
        # Store metadata
        if metadata is None:
            metadata = [{"text": text, "index": i} for i, text in enumerate(texts)]
        
        # Add timestamp and prefix to metadata
        for i, meta in enumerate(metadata):
            meta["prefix"] = prefix
            meta["added_at"] = datetime.now().isoformat()
            if "text" not in meta:
                meta["text"] = texts[i] if i < len(texts) else ""
        
        self.metadata[prefix].extend(metadata)
        
        # Save to disk
        self._save_index(prefix)
        
        return True
    
    def search(
        self,
        query_vector: np.ndarray,
        prefix: Optional[str] = None,
        k: int = 5,
        score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search in index(es)
        
        Args:
            query_vector: Query embedding vector
            prefix: Specific prefix to search, or None for all
            k: Number of results to return
            score_threshold: Minimum similarity score
            
        Returns:
            List of search results with metadata
        """
        if prefix:
            prefixes = [prefix]
        else:
            prefixes = list(self.indexes.keys())
        
        all_results = []
        
        for pref in prefixes:
            if pref not in self.indexes:
                continue
            
            index = self.indexes[pref]
            
            # Normalize query vector for cosine similarity
            query = query_vector.reshape(1, -1).astype('float32')
            if self.similarity_metric == "cosine":
                faiss.normalize_L2(query)
            
            # Search
            distances, indices = index.search(query, min(k, index.ntotal))
            
            # Get results with metadata
            for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
                if idx < 0:  # Invalid index
                    continue
                
                score = float(dist) if self.similarity_metric == "cosine" else float(1 / (1 + dist))
                
                if score >= score_threshold:
                    result = {
                        "prefix": pref,
                        "index": int(idx),
                        "score": score,
                        "distance": float(dist),
                        "metadata": self.metadata[pref][idx] if idx < len(self.metadata[pref]) else {}
                    }
                    all_results.append(result)
        
        # Sort by score (descending)
        all_results.sort(key=lambda x: x["score"], reverse=True)
        
        return all_results[:k]
    
    def parallel_search(
        self,
        query_vector: np.ndarray,
        prefixes: List[str],
        k: int = 5,
        score_threshold: float = 0.0
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parallel search across multiple indexes
        
        Args:
            query_vector: Query embedding vector
            prefixes: List of prefixes to search
            k: Number of results per prefix
            score_threshold: Minimum similarity score
            
        Returns:
            Dictionary mapping prefix to search results
        """
        from concurrent.futures import ThreadPoolExecutor
        
        results = {}
        
        def search_prefix(pref: str) -> Tuple[str, List[Dict[str, Any]]]:
            return pref, self.search(query_vector, prefix=pref, k=k, score_threshold=score_threshold)
        
        with ThreadPoolExecutor(max_workers=len(prefixes)) as executor:
            futures = {executor.submit(search_prefix, pref): pref for pref in prefixes}
            for future in futures:
                pref, result = future.result()
                results[pref] = result
        
        return results
    
    def get_index_stats(self, prefix: str) -> Dict[str, Any]:
        """Get statistics for an index"""
        if prefix not in self.indexes:
            return {}
        
        index = self.indexes[prefix]
        return {
            "prefix": prefix,
            "vector_count": index.ntotal,
            "dimension": index.d,
            "metadata_count": len(self.metadata.get(prefix, []))
        }
    
    def delete_index(self, prefix: str) -> bool:
        """Delete an index"""
        if prefix not in self.indexes:
            return False
        
        del self.indexes[prefix]
        
        # Delete files
        if prefix in self.index_paths:
            index_path = self.index_paths[prefix]
            if index_path.exists():
                index_path.unlink()
            metadata_path = index_path.with_suffix(".metadata")
            if metadata_path.exists():
                metadata_path.unlink()
        
        if prefix in self.metadata:
            del self.metadata[prefix]
        
        if prefix in self.index_paths:
            del self.index_paths[prefix]
        
        print(f"Deleted index: {prefix}")
        return True
    
    def _save_index(self, prefix: str):
        """Save index to disk"""
        if prefix not in self.indexes:
            return
        
        index_path = self.index_paths[prefix]
        faiss.write_index(self.indexes[prefix], str(index_path))
        
        # Save metadata
        metadata_path = index_path.with_suffix(".metadata")
        with open(metadata_path, 'wb') as f:
            pickle.dump(self.metadata[prefix], f)
    
    def save_all(self):
        """Save all indexes to disk"""
        for prefix in self.indexes.keys():
            self._save_index(prefix)
    
    def list_indexes(self) -> List[str]:
        """List all available index prefixes"""
        return list(self.indexes.keys())

