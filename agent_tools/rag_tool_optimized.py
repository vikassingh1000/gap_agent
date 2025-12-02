"""
Optimized RAG Tool for Gap Assessment Agent (Production-Grade)
Reduces LLM calls from 71 to 5-10 per request using smart filtering and batching
"""
import numpy as np
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor
import time

from vector_db.pinecone_manager import PineconeManager
from utilities.embedding_client import EmbeddingClient
from utilities.google_gemini_client import GoogleGeminiClient


class OptimizedRAGTool:
    """Production-grade RAG tool with minimal LLM usage"""
    
    def __init__(
        self,
        agent_config: Dict[str, Any],
        vector_db: PineconeManager,
        embedding_client: EmbeddingClient,
        gemini_client: GoogleGeminiClient
    ):
        """
        Initialize optimized RAG tool
        
        Args:
            agent_config: Agent configuration dictionary
            vector_db: PineconeManager instance
            embedding_client: Embedding client instance
            gemini_client: GoogleGeminiClient instance (for LLM scoring)
        """
        self.agent_config = agent_config
        self.rag_config = agent_config.get("rag", {})
        self.vector_db = vector_db
        self.embedding_client = embedding_client
        self.gemini_client = gemini_client
        
        # Configuration
        self.min_groundedness = self.rag_config.get("min_groundedness_score", 3)
        self.min_relevance = self.rag_config.get("min_relevance_score", 3)
        self.top_k = self.rag_config.get("top_k_results", 5)
        self.parallel_search = self.rag_config.get("parallel_search", True)
        
        # Optimization settings
        self.similarity_threshold = self.rag_config.get("similarity_threshold", 0.7)
        self.use_llm_scoring = self.rag_config.get("use_llm_scoring", True)
        self.max_llm_scored_results = self.rag_config.get("max_llm_scored_results", 5)
        self.skip_comparison_for_low_scores = self.rag_config.get("skip_comparison_for_low_scores", True)
        self.max_comparisons = self.rag_config.get("max_comparisons", 5)  # Max benchmark results to compare
        
        # Metrics tracking
        self.llm_call_count = 0
    
    def search(
        self,
        query: str,
        primary_prefix: str = "GAP_BP",
        benchmark_prefixes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Search across indexes with optimized filtering
        
        Args:
            query: Search query
            primary_prefix: Primary company prefix (default: GAP_BP)
            benchmark_prefixes: List of benchmark company prefixes
            
        Returns:
            Dictionary with search results and scores
        """
        # Reset LLM call count for this search
        self.llm_call_count = 0
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
        
        # Optimized scoring and filtering
        scored_results = self._optimized_score_and_filter(
            query,
            primary_results,
            benchmark_results
        )
        
        return scored_results
    
    def _optimized_score_and_filter(
        self,
        query: str,
        primary_results: List[Dict[str, Any]],
        benchmark_results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Optimized scoring: Use similarity first, LLM only for top results
        
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
        
        # Step 1: Filter by similarity threshold (no LLM)
        filtered_primary = self._filter_by_similarity(primary_results)
        filtered_benchmarks = {}
        for prefix, results in benchmark_results.items():
            filtered_benchmarks[prefix] = self._filter_by_similarity(results)
        
        # Step 2: Use similarity scores as relevance/groundedness proxy
        # Convert similarity (0-1) to score (1-5)
        llm_scored_count = 0
        for result in filtered_primary:
            similarity = result.get("score", 0)
            # Map similarity to 1-5 scale
            relevance = max(1, min(5, int(similarity * 5) + 1))
            groundedness = relevance  # Use similarity as groundedness proxy
            result["relevance"] = relevance
            result["groundedness"] = groundedness
            result["is_primary"] = True
            
            # Only use LLM scoring for top results if enabled AND similarity is high enough
            if (self.use_llm_scoring and 
                llm_scored_count < self.max_llm_scored_results and
                similarity >= 0.6):  # Only LLM score high-similarity results
                llm_scored = self._llm_score_result(query, result, is_primary=True)
                if llm_scored:
                    result["relevance"] = llm_scored.get("relevance", relevance)
                    result["groundedness"] = llm_scored.get("groundedness", groundedness)
                    llm_scored_count += 1
            
            if result["groundedness"] >= self.min_groundedness and result["relevance"] >= self.min_relevance:
                all_results["primary"].append(result)
        
        # Step 3: Score benchmark results (similarity-first approach)
        total_llm_scored = 0
        for prefix, results in filtered_benchmarks.items():
            all_results["benchmarks"][prefix] = []
            
            for result in results:
                similarity = result.get("score", 0)
                relevance = max(1, min(5, int(similarity * 5) + 1))
                groundedness = relevance
                result["relevance"] = relevance
                result["groundedness"] = groundedness
                result["is_primary"] = False
                
                # Only use LLM for top results across all benchmarks (not per benchmark)
                # Only score high-similarity results
                if (self.use_llm_scoring and 
                    total_llm_scored < self.max_llm_scored_results and
                    similarity >= 0.6):
                    llm_scored = self._llm_score_result(query, result, is_primary=False)
                    if llm_scored:
                        result["relevance"] = llm_scored.get("relevance", relevance)
                        result["groundedness"] = llm_scored.get("groundedness", groundedness)
                        total_llm_scored += 1
                
                if result["groundedness"] >= self.min_groundedness and result["relevance"] >= self.min_relevance:
                    all_results["benchmarks"][prefix].append(result)
        
        return all_results
    
    def _filter_by_similarity(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter results by similarity threshold"""
        return [
            r for r in results 
            if r.get("score", 0) >= self.similarity_threshold
        ]
    
    def _llm_score_result(
        self,
        query: str,
        result: Dict[str, Any],
        is_primary: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Score a single result using LLM (only for top results)
        
        Args:
            query: Original query
            result: Search result dictionary
            is_primary: Whether this is from primary index
            
        Returns:
            Dictionary with LLM scores, or None if failed
        """
        text = result.get("metadata", {}).get("text", "")[:500]
        
        # Combined scoring prompt (reduces from 2 calls to 1)
        scoring_prompt = f"""
        Rate this text excerpt for both groundedness and relevance on a scale of 1-5:
        Query: {query}
        Text: {text}
        
        Respond with ONLY two numbers separated by a comma: groundedness,relevance
        Where:
        - Groundedness (1-5): How well is the result supported by the source?
        - Relevance (1-5): How relevant is this to the query?
        
        Example response: 4,5
        """
        
        try:
            self.llm_call_count += 1  # Track LLM call
            response = self.gemini_client.generate(scoring_prompt)
            parts = response.strip().split(',')
            if len(parts) == 2:
                groundedness = max(1, min(5, int(parts[0].strip())))
                relevance = max(1, min(5, int(parts[1].strip())))
                return {"groundedness": groundedness, "relevance": relevance}
        except Exception as e:
            # Fallback to similarity-based scores
            pass
        
        return None
    
    def compare_with_primary(
        self,
        query: str,
        primary_results: List[Dict[str, Any]],
        benchmark_results: Dict[str, List[Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Optimized comparison: Only compare top benchmark results
        
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
        
        # Compare with top benchmark results only
        comparison_count = 0
        for prefix, results in benchmark_results.items():
            benchmark_name = prefix.replace("GAP_", "")
            comparison["benchmark_comparisons"][benchmark_name] = []
            
            # Only compare top results per benchmark
            top_results = results[:min(self.max_comparisons, len(results))]
            
            for result in top_results:
                # Skip comparison for low-scoring results if enabled
                if self.skip_comparison_for_low_scores:
                    if result.get("relevance", 0) < self.min_relevance:
                        continue
                
                comparison_item = {
                    "text": result.get("metadata", {}).get("text", ""),
                    "scores": {
                        "groundedness": result.get("groundedness", 0),
                        "relevance": result.get("relevance", 0),
                        "similarity": result.get("score", 0)
                    },
                    "comparison_with_primary": self._quick_compare(
                        result,
                        primary_results
                    )
                }
                comparison["benchmark_comparisons"][benchmark_name].append(comparison_item)
                comparison_count += 1
                
                # Limit total comparisons
                if comparison_count >= self.max_comparisons * len(benchmark_results):
                    break
            
            if comparison_count >= self.max_comparisons * len(benchmark_results):
                break
        
        return comparison
    
    def _quick_compare(
        self,
        benchmark_result: Dict[str, Any],
        primary_results: List[Dict[str, Any]]
    ) -> str:
        """
        Quick comparison using similarity and text analysis (no LLM)
        Only use LLM for critical comparisons if needed
        """
        benchmark_text = benchmark_result.get("metadata", {}).get("text", "")[:200]
        benchmark_score = benchmark_result.get("score", 0)
        
        primary_texts = [r.get("metadata", {}).get("text", "")[:200] for r in primary_results[:2]]
        primary_scores = [r.get("score", 0) for r in primary_results[:2]]
        
        # Simple text-based comparison
        if benchmark_score > max(primary_scores, default=0):
            return f"Benchmark finding shows stronger alignment (score: {benchmark_score:.2f}) compared to primary company approach."
        elif benchmark_score < min(primary_scores, default=1):
            return f"Benchmark finding indicates potential gap (score: {benchmark_score:.2f}) compared to primary company approach."
        else:
            return f"Benchmark finding is similar to primary company approach (score: {benchmark_score:.2f})."
    
    def _compare_with_primary_findings_llm(
        self,
        benchmark_result: Dict[str, Any],
        primary_results: List[Dict[str, Any]]
    ) -> str:
        """LLM-based comparison (only for critical results)"""
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
            return comparison[:500]
        except Exception as e:
            return f"Comparison analysis unavailable due to API error."

