"""
RAG Tool for Gap Assessment Agent
Retrieves relevant information from vector DB with parallel search
"""
import numpy as np
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

from vector_db.pinecone_manager import PineconeManager
from utilities.embedding_client import EmbeddingClient
from utilities.google_gemini_client import GoogleGeminiClient


class RAGTool:
    """RAG tool with parallel search and groundedness/relevance scoring"""
    
    def __init__(
        self,
        agent_config: Dict[str, Any],
        vector_db: PineconeManager,
        embedding_client: EmbeddingClient,
        gemini_client: GoogleGeminiClient
    ):
        """
        Initialize RAG tool
        
        Args:
            agent_config: Agent configuration dictionary
            vector_db: PineconeManager instance
            embedding_client: EmbeddingClient instance
            gemini_client: GoogleGeminiClient instance (for LLM scoring)
        """
        self.agent_config = agent_config
        self.rag_config = agent_config.get("rag", {})
        self.vector_db = vector_db
        self.embedding_client = embedding_client
        self.gemini_client = gemini_client
        
        self.min_groundedness = self.rag_config.get("min_groundedness_score", 3)
        self.min_relevance = self.rag_config.get("min_relevance_score", 3)
        self.top_k = self.rag_config.get("top_k_results", 5)
        self.parallel_search = self.rag_config.get("parallel_search", True)
    
    def search(
        self,
        query: str,
        primary_prefix: str = "GAP_BP",
        benchmark_prefixes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search across indexes with parallel execution
        
        Args:
            query: Search query
            primary_prefix: Primary company prefix (default: GAP_BP)
            benchmark_prefixes: List of benchmark company prefixes
            
        Returns:
            Dictionary with search results and scores
        """
        if benchmark_prefixes is None:
            companies_config = self.agent_config.get("companies", {})
            benchmarks = companies_config.get("benchmark_companies", [])
            benchmark_prefixes = [f"GAP_{b.upper()}" for b in benchmarks]
        
        # Generate query embedding using sentence-transformers (no quota!)
        try:
            query_embedding = self.embedding_client.embed_text(query)
            query_vector = np.array(query_embedding).astype('float32')
        except Exception as e:
            return {
                "primary": [],
                "benchmarks": {},
                "error": f"Error generating query embedding: {str(e)}"
            }
        
        # Search primary index
        primary_results = self.vector_db.search(
            query_vector,
            prefix=primary_prefix,
            k=self.top_k
        )
        
        # Parallel search benchmark indexes
        if self.parallel_search:
            benchmark_results = self.vector_db.parallel_search(
                query_vector,
                prefixes=benchmark_prefixes,
                k=self.top_k
            )
        else:
            benchmark_results = {}
            for prefix in benchmark_prefixes:
                results = self.vector_db.search(
                    query_vector,
                    prefix=prefix,
                    k=self.top_k
                )
                benchmark_results[prefix] = results
        
        # Score and filter results
        scored_results = self._score_and_filter_results(
            query,
            primary_results,
            benchmark_results
        )
        
        return scored_results
    
    def _score_and_filter_results(
        self,
        query: str,
        primary_results: List[Dict[str, Any]],
        benchmark_results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Score results for groundedness and relevance, filter by thresholds
        
        Args:
            query: Original query
            primary_results: Results from primary index
            benchmark_results: Results from benchmark indexes
            
        Returns:
            Dictionary with filtered and scored results
        """
        all_results = {
            "primary": [],
            "benchmarks": {}
        }
        
        # Score primary results with rate limiting
        import time
        for i, result in enumerate(primary_results):
            scored = self._score_result(query, result, is_primary=True)
            if scored["groundedness"] >= self.min_groundedness and scored["relevance"] >= self.min_relevance:
                all_results["primary"].append(scored)
            # Add small delay to avoid hitting rate limits
            if i < len(primary_results) - 1:
                time.sleep(0.5)
        
        # Score benchmark results with rate limiting
        for prefix, results in benchmark_results.items():
            all_results["benchmarks"][prefix] = []
            for i, result in enumerate(results):
                scored = self._score_result(query, result, is_primary=False)
                if scored["groundedness"] >= self.min_groundedness and scored["relevance"] >= self.min_relevance:
                    all_results["benchmarks"][prefix].append(scored)
                # Add small delay to avoid hitting rate limits
                if i < len(results) - 1:
                    time.sleep(0.5)
        
        return all_results
    
    def _score_result(
        self,
        query: str,
        result: Dict[str, Any],
        is_primary: bool = False
    ) -> Dict[str, Any]:
        """
        Score a result for groundedness and relevance
        
        Args:
            query: Original query
            result: Search result dictionary
            is_primary: Whether this is from primary index
            
        Returns:
            Result dictionary with scores added
        """
        text = result.get("metadata", {}).get("text", "")
        
        # Use similarity score as fallback if LLM scoring fails
        similarity_score = result.get("score", 0)
        default_groundedness = max(3, int(similarity_score * 5)) if similarity_score > 0 else 3
        default_relevance = max(3, int(similarity_score * 5)) if similarity_score > 0 else 3
        
        # Score groundedness (1-5): How well is the result supported by the source?
        groundedness_prompt = f"""
        Rate the groundedness of this text excerpt (how well it's supported by the source) on a scale of 1-5:
        Query: {query}
        Text: {text[:500]}
        
        Respond with only a number from 1 to 5, where:
        1 = Not grounded, likely speculation
        2 = Weakly grounded, minimal support
        3 = Moderately grounded, some support
        4 = Well grounded, strong support
        5 = Highly grounded, excellent support
        """
        
        try:
            groundedness_response = self.gemini_client.generate(groundedness_prompt)
            groundedness = int(groundedness_response.strip())
            groundedness = max(1, min(5, groundedness))  # Clamp to 1-5
        except Exception as e:
            # Use default if quota exceeded or other error
            if 'quota' in str(e).lower() or '429' in str(e):
                groundedness = default_groundedness
            else:
                groundedness = default_groundedness
        
        # Score relevance (1-5): How relevant is this to the query?
        relevance_prompt = f"""
        Rate the relevance of this text to the query on a scale of 1-5:
        Query: {query}
        Text: {text[:500]}
        
        Respond with only a number from 1 to 5, where:
        1 = Not relevant
        2 = Slightly relevant
        3 = Moderately relevant
        4 = Highly relevant
        5 = Extremely relevant
        """
        
        try:
            relevance_response = self.gemini_client.generate(relevance_prompt)
            relevance = int(relevance_response.strip())
            relevance = max(1, min(5, relevance))  # Clamp to 1-5
        except Exception as e:
            # Use default if quota exceeded or other error
            if 'quota' in str(e).lower() or '429' in str(e):
                relevance = default_relevance
            else:
                relevance = default_relevance
        
        result["groundedness"] = groundedness
        result["relevance"] = relevance
        result["is_primary"] = is_primary
        
        return result
    
    def compare_with_primary(
        self,
        query: str,
        primary_results: List[Dict[str, Any]],
        benchmark_results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Compare benchmark results with primary (BP) results
        
        Args:
            query: Original query
            primary_results: Results from primary index (BP)
            benchmark_results: Results from benchmark indexes
            
        Returns:
            Comparison analysis
        """
        comparison = {
            "query": query,
            "primary_findings": [],
            "benchmark_comparisons": {},
            "gaps_identified": []
        }
        
        # Extract primary findings
        for result in primary_results:
            finding = {
                "text": result.get("metadata", {}).get("text", ""),
                "scores": {
                    "groundedness": result.get("groundedness", 0),
                    "relevance": result.get("relevance", 0),
                    "similarity": result.get("score", 0)
                }
            }
            comparison["primary_findings"].append(finding)
        
        # Compare with each benchmark
        for prefix, results in benchmark_results.items():
            benchmark_name = prefix.replace("GAP_", "")
            comparison["benchmark_comparisons"][benchmark_name] = []
            
            for result in results:
                comparison_item = {
                    "text": result.get("metadata", {}).get("text", ""),
                    "scores": {
                        "groundedness": result.get("groundedness", 0),
                        "relevance": result.get("relevance", 0),
                        "similarity": result.get("score", 0)
                    },
                    "comparison_with_primary": self._compare_with_primary_findings(
                        result,
                        primary_results
                    )
                }
                comparison["benchmark_comparisons"][benchmark_name].append(comparison_item)
        
        return comparison
    
    def _compare_with_primary_findings(
        self,
        benchmark_result: Dict[str, Any],
        primary_results: List[Dict[str, Any]]
    ) -> str:
        """Generate comparison text between benchmark and primary findings"""
        benchmark_text = benchmark_result.get("metadata", {}).get("text", "")[:200]
        primary_texts = [r.get("metadata", {}).get("text", "")[:200] for r in primary_results[:2]]
        
        comparison_prompt = f"""
        Compare this benchmark finding with the primary company findings:
        
        Benchmark Finding: {benchmark_text}
        
        Primary Findings:
        {chr(10).join([f"- {text}" for text in primary_texts])}
        
        Provide a brief comparison (2-3 sentences) highlighting differences or gaps.
        """
        
        try:
            comparison = self.gemini_client.generate(comparison_prompt)
            return comparison[:500]  # Limit length
        except Exception as e:
            # Return simple comparison if LLM fails
            if 'quota' in str(e).lower() or '429' in str(e):
                return f"Benchmark finding differs from primary company approach. Further analysis needed when API quota is available."
            return f"Comparison analysis unavailable due to API error."

