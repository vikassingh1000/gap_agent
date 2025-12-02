"""
Gap Assessment Agent using Google ADK LlmAgent
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    # Try Google ADK imports - API may vary
    try:
        from google.genai import types
        from google.genai.client import Client
        from google.genai.types import Tool, FunctionDeclaration, Schema
        ADK_AVAILABLE = True
        ADK_IMPORT_STYLE = "new"
    except ImportError:
        try:
            # Alternative import style
            import google.generativeai as genai
            ADK_AVAILABLE = True
            ADK_IMPORT_STYLE = "gemini"
        except ImportError:
            ADK_AVAILABLE = False
            ADK_IMPORT_STYLE = None
            print("Warning: Google ADK not installed. Install with: pip install google-genai")
except Exception as e:
    ADK_AVAILABLE = False
    ADK_IMPORT_STYLE = None
    print(f"Warning: Error importing Google ADK: {e}")

from agent_tools import ExtractionTool, OptimizedRAGTool
from vector_db.pinecone_manager import PineconeManager
from utilities.google_gemini_client import GoogleGeminiClient
from utilities.embedding_client import EmbeddingClient
from utilities.logger import GapAssessmentLogger


class GapAssessmentAgent:
    """Gap Assessment Agent using Google ADK"""
    api_key: object

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize Gap Assessment Agent
        
        Args:
            config_path: Path to agent configuration file
        """
        # Note: We use direct Gemini API calls for now
        # Full ADK integration can be added when needed
        
        # Load configuration
        if config_path is None:
            config_path = Path(__file__).parent.parent / "config" / "agent_config.json"
        
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        
        # Initialize vector DB (Pinecone)
        vector_db_config = self.config["vector_db"]
        if vector_db_config["type"] != "pinecone":
            raise ValueError("Pinecone is required. Update config to use Pinecone.")
        
        self.vector_db = PineconeManager(
            api_key=vector_db_config["api_key"],
            dimension=vector_db_config["dimension"],
            similarity_metric=vector_db_config["similarity_metric"],
            environment=vector_db_config.get("environment", "us-east-1")
        )
        
        # Initialize embedding client (sentence-transformers)
        embedding_config = self.config["agent"]["embeddings"]
        self.embedding_client = EmbeddingClient(
            model_name=embedding_config.get("model", "all-mpnet-base-v2")
        )
        
        # Get API key from config for LLM (still using Gemini for text generation)
        api_key = self.config["agent"]["llm"].get("api_key")
        if not api_key:
            raise ValueError("API key required. Set 'api_key' in config/agent_config.json under 'agent.llm' section.")
        
        # Initialize Gemini client for LLM (text generation only, not embeddings)
        self.gemini_client = GoogleGeminiClient(
            api_key=api_key,
            model=self.config["agent"]["llm"]["model"],
            temperature=self.config["agent"]["llm"]["temperature"]
        )
        
        self.extraction_tool = ExtractionTool(self.config, self.embedding_client)
        # Use optimized RAG tool for production-grade performance
        self.rag_tool = OptimizedRAGTool(self.config, self.vector_db, self.embedding_client, self.gemini_client)
        self.logger = GapAssessmentLogger(self.config)
        
        # Metrics tracking
        self.metrics = {
            "llm_calls": 0,
            "start_time": None,
            "end_time": None,
            "latency_seconds": 0
        }
        
        self.api_key = api_key
        
        # Create agent with tools (simplified for now - will use direct LLM calls)
        # Note: Full ADK integration may require additional setup
        self.agent = None  # Will use direct Gemini calls for now
    
    def _create_agent(self):
        """Create ADK agent with tools"""
        # For now, we'll use a simplified approach with direct LLM calls
        # Full ADK integration can be added when the API is finalized
        # The agent logic is handled in assess_gaps method
        return None
    
    def _create_extraction_tool(self) -> Tool:
        """Create extraction tool for ADK"""
        extraction_schema = Schema(
            type="object",
            properties={
                "company_key": Schema(type="string", description="Company identifier (bp, kpmg, ey, deloitte, pwc)"),
                "force": Schema(type="boolean", description="Force extraction even if recent data exists")
            },
            required=["company_key"]
        )
        
        function_declaration = FunctionDeclaration(
            name="extract_company_data",
            description="Extract data from company websites and store in vector database. Use this to gather fresh data when needed.",
            parameters=extraction_schema
        )
        
        return Tool(function_declarations=[function_declaration])
    
    def _create_rag_tool(self) -> Tool:
        """Create RAG tool for ADK"""
        rag_schema = Schema(
            type="object",
            properties={
                "query": Schema(type="string", description="Search query for gap assessment"),
                "primary_prefix": Schema(type="string", description="Primary company prefix (default: GAP_BP)"),
                "benchmark_prefixes": Schema(
                    type="array",
                    items=Schema(type="string"),
                    description="List of benchmark company prefixes to search"
                )
            },
            required=["query"]
        )
        
        function_declaration = FunctionDeclaration(
            name="search_and_compare",
            description="Search vector database for relevant information and compare primary company (BP) with benchmarks. Returns results with groundedness and relevance scores.",
            parameters=rag_schema
        )
        
        return Tool(function_declarations=[function_declaration])
    
    def _handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Handle tool calls from agent"""
        if tool_name == "extract_company_data":
            company_key = arguments.get("company_key", "bp")
            force = arguments.get("force", False)
            result = self.extraction_tool.extract_company_data(company_key, force=force)
            self.logger.log_extraction(company_key, result.get("status", "unknown"), result)
            return json.dumps(result)
        
        elif tool_name == "search_and_compare":
            query = arguments.get("query", "")
            primary_prefix = arguments.get("primary_prefix", "GAP_BP")
            benchmark_prefixes = arguments.get("benchmark_prefixes")
            
            # Search
            search_results = self.rag_tool.search(query, primary_prefix, benchmark_prefixes)
            
            # Compare
            comparison = self.rag_tool.compare_with_primary(
                query,
                search_results["primary"],
                search_results["benchmarks"]
            )
            
            # Log
            indexes_searched = [primary_prefix] + (benchmark_prefixes or [])
            self.logger.log_index_usage(
                query,
                indexes_searched,
                {
                    "primary": len(search_results["primary"]),
                    **{k: len(v) for k, v in search_results["benchmarks"].items()}
                }
            )
            self.logger.log_comparison(query, primary_prefix, benchmark_prefixes or [], comparison)
            
            return json.dumps(comparison, indent=2)
        
        else:
            return f"Unknown tool: {tool_name}"
    
    def assess_gaps(
        self,
        query: str,
        force_extraction: bool = False
    ) -> Dict[str, Any]:
        """
        Perform gap assessment with metrics tracking
        
        Args:
            query: Assessment query/question
            force_extraction: Force data extraction even if recent
            
        Returns:
            Gap assessment results with metrics
        """
        import time
        
        # Reset and start metrics tracking
        self.metrics = {
            "llm_calls": 0,
            "start_time": time.time(),
            "end_time": None,
            "latency_seconds": 0,
            "search_results_count": 0,
            "comparison_count": 0
        }
        
        # Check if extraction needed
        companies_config = self.config.get("companies", {})
        primary = companies_config.get("primary", "bp")
        
        # Check extraction dates and force_refresh config
        should_extract = self.extraction_tool._should_extract(primary, force_extraction)
        
        # Only extract if should_extract is True OR force_extraction is explicitly True
        # Note: force_refresh=False in config will make should_extract=False
        if should_extract or force_extraction:
            self.logger.log_agent_action("extraction_check", {
                "should_extract": should_extract,
                "force_extraction": force_extraction,
                "force_refresh": self.config.get("extraction", {}).get("force_refresh", False)
            })
            
            # Extract data if needed
            if force_extraction or should_extract:
                print("Extracting data...")
                extraction_result = self.extraction_tool.extract_all_companies(force=force_extraction)
                self.logger.log_agent_action("extraction_complete", extraction_result)
        else:
            # Log that extraction was skipped
            force_refresh = self.config.get("extraction", {}).get("force_refresh", False)
            if not force_refresh:
                print("Extraction skipped: force_refresh is False in config")
            else:
                print("Extraction skipped: Recent data exists")
        
        # Perform RAG search
        print("Searching vector database...")
        search_results = self.rag_tool.search(query)
        
        # Track search results
        self.metrics["search_results_count"] = len(search_results.get("primary", [])) + sum(
            len(results) for results in search_results.get("benchmarks", {}).values()
        )
        
        # Check if search failed due to quota
        if search_results.get("error"):
            self.metrics["end_time"] = time.time()
            self.metrics["latency_seconds"] = self.metrics["end_time"] - self.metrics["start_time"]
            return {
                "query": query,
                "error": search_results.get("error"),
                "status": "quota_exceeded",
                "message": "Cannot perform search due to API quota limits. Please try again later.",
                "metrics": self.metrics
            }
        
        # Compare with benchmarks
        comparison = self.rag_tool.compare_with_primary(
            query,
            search_results["primary"],
            search_results["benchmarks"]
        )
        
        # Track comparison count
        self.metrics["comparison_count"] = sum(
            len(comps) for comps in comparison.get("benchmark_comparisons", {}).values()
        )
        
        # Get LLM call count from RAG tool if available
        if hasattr(self.rag_tool, 'llm_call_count'):
            self.metrics["llm_calls"] = self.rag_tool.llm_call_count
        
        # Generate gap assessment using LLM
        print("Generating gap assessment...")
        try:
            assessment = self._generate_assessment(query, comparison)
            self.metrics["llm_calls"] += 1  # Final assessment call
        except Exception as e:
            error_msg = str(e)
            if 'quota' in error_msg.lower() or '429' in error_msg:
                self.metrics["end_time"] = time.time()
                self.metrics["latency_seconds"] = self.metrics["end_time"] - self.metrics["start_time"]
                return {
                    "query": query,
                    "error": "API quota exceeded during assessment generation",
                    "status": "quota_exceeded",
                    "search_results": search_results,
                    "message": "Search completed but assessment generation failed due to quota limits.",
                    "metrics": self.metrics
                }
            raise
        
        # Finalize metrics
        self.metrics["end_time"] = time.time()
        self.metrics["latency_seconds"] = self.metrics["end_time"] - self.metrics["start_time"]
        
        return {
            "query": query,
            "assessment": assessment,
            "comparison": comparison,
            "search_results": search_results,
            "metrics": self.metrics
        }
    
    def _generate_assessment(
        self,
        query: str,
        comparison: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate gap assessment using LLM and parse the response"""
        import re
        
        prompt = f"""
        You are an expert gap assessment consultant specializing in tax technology and compliance digitization.
        
        Based on the following comparison data, provide a comprehensive gap assessment:
        
        Query: {query}
        
        Primary Company (BP) Findings:
        {json.dumps(comparison.get('primary_findings', []), indent=2)}
        
        Benchmark Comparisons:
        {json.dumps(comparison.get('benchmark_comparisons', {}), indent=2)}
        
        Provide a gap assessment with:
        1. Identified gaps (with risk scores 1-10)
        2. Current state assessment
        3. Target state (based on benchmarks)
        4. Recommendations
        5. Priority levels (Critical/High/Medium/Low)
        
        Format as JSON with the following structure:
        {{
            "gaps": [
                {{
                    "gap_id": "GAP-001",
                    "description": "...",
                    "current_state": "...",
                    "target_state": "...",
                    "risk_score": 1-10,
                    "priority": "Critical|High|Medium|Low",
                    "recommendations": ["..."],
                    "benchmark_source": "..."
                }}
            ],
            "summary": {{
                "total_gaps": 0,
                "critical_gaps": 0,
                "high_priority_gaps": 0,
                "overall_risk_score": 1-10
            }}
        }}
        """
        
        response = self.gemini_client.generate_structured(prompt)
        
        # Parse the response - handle both raw JSON string and parsed dict
        parsed_assessment = None
        
        if isinstance(response, dict):
            # Check if it has raw_response with JSON string
            if "raw_response" in response:
                raw_text = response["raw_response"]
                # Extract JSON from markdown code blocks
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', raw_text, re.DOTALL)
                if json_match:
                    try:
                        parsed_assessment = json.loads(json_match.group(1))
                    except:
                        # Try to find JSON without markdown
                        json_match = re.search(r'(\{.*\})', raw_text, re.DOTALL)
                        if json_match:
                            try:
                                parsed_assessment = json.loads(json_match.group(1))
                            except:
                                pass
                else:
                    # Try to parse the entire raw_response as JSON
                    try:
                        parsed_assessment = json.loads(raw_text)
                    except:
                        pass
            else:
                # Already parsed
                parsed_assessment = response
        elif isinstance(response, str):
            # Try to extract JSON from string
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                try:
                    parsed_assessment = json.loads(json_match.group(1))
                except:
                    pass
            else:
                try:
                    parsed_assessment = json.loads(response)
                except:
                    pass
        
        # Return structured format
        if parsed_assessment and isinstance(parsed_assessment, dict):
            return {
                "gaps": parsed_assessment.get("gaps", []),
                "summary": parsed_assessment.get("summary", {}),
                "raw_response": response.get("raw_response", str(response)) if isinstance(response, dict) else str(response)
            }
        else:
            # Fallback to raw response if parsing failed
            return {
                "gaps": [],
                "summary": {
                    "total_gaps": 0,
                    "critical_gaps": 0,
                    "high_priority_gaps": 0,
                    "overall_risk_score": 0
                },
                "raw_response": response.get("raw_response", str(response)) if isinstance(response, dict) else str(response),
                "parse_error": "Failed to parse assessment response"
            }
    
    def run(self, query: str, force_extraction: bool = False) -> Dict[str, Any]:
        """
        Run gap assessment agent
        
        Args:
            query: Assessment query
            force_extraction: Force data extraction
            
        Returns:
            Complete assessment results
        """
        return self.assess_gaps(query, force_extraction)

