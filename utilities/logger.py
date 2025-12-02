"""
Logging system for Gap Assessment Agent
"""
import os
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional


class GapAssessmentLogger:
    """Custom logger for gap assessment agent"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize logger
        
        Args:
            config: Logging configuration from agent_config
        """
        self.config = config
        self.logging_config = config.get("logging", {})
        
        if not self.logging_config.get("enabled", True):
            return
        
        # Setup logging
        log_file = self.logging_config.get("log_file", "logs/gap_assessment_agent.log")
        log_level = self.logging_config.get("log_level", "INFO")
        
        # Create logs directory
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("GapAssessmentAgent")
        
        # Track index usage and comparisons
        self.index_usage_log: List[Dict[str, Any]] = []
        self.comparison_log: List[Dict[str, Any]] = []
    
    def log_index_usage(
        self,
        query: str,
        indexes_searched: List[str],
        results_count: Dict[str, int]
    ):
        """Log which indexes were used for a query"""
        if not self.logging_config.get("track_index_usage", True):
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "indexes_searched": indexes_searched,
            "results_count": results_count
        }
        
        self.index_usage_log.append(log_entry)
        self.logger.info(f"Index usage: {json.dumps(log_entry, indent=2)}")
    
    def log_comparison(
        self,
        query: str,
        primary_prefix: str,
        benchmark_prefixes: List[str],
        comparison_results: Dict[str, Any]
    ):
        """Log comparison between BP and benchmark results"""
        if not self.logging_config.get("track_comparisons", True):
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "primary_index": primary_prefix,
            "benchmark_indexes": benchmark_prefixes,
            "primary_results_count": len(comparison_results.get("primary_findings", [])),
            "benchmark_results": {
                prefix: len(results) 
                for prefix, results in comparison_results.get("benchmark_comparisons", {}).items()
            },
            "gaps_identified_count": len(comparison_results.get("gaps_identified", []))
        }
        
        self.comparison_log.append(log_entry)
        self.logger.info(f"Comparison: {json.dumps(log_entry, indent=2)}")
    
    def log_extraction(
        self,
        company_key: str,
        status: str,
        details: Dict[str, Any]
    ):
        """Log data extraction event"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "company": company_key,
            "status": status,
            "details": details
        }
        
        self.logger.info(f"Extraction: {json.dumps(log_entry, indent=2)}")
    
    def log_agent_action(
        self,
        action: str,
        details: Dict[str, Any]
    ):
        """Log agent action"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details
        }
        
        self.logger.info(f"Agent action: {json.dumps(log_entry, indent=2)}")
    
    def get_index_usage_summary(self) -> Dict[str, Any]:
        """Get summary of index usage"""
        if not self.index_usage_log:
            return {"message": "No index usage logged"}
        
        index_counts = {}
        for entry in self.index_usage_log:
            for index in entry.get("indexes_searched", []):
                index_counts[index] = index_counts.get(index, 0) + 1
        
        return {
            "total_queries": len(self.index_usage_log),
            "index_usage_counts": index_counts
        }
    
    def get_comparison_summary(self) -> Dict[str, Any]:
        """Get summary of comparisons"""
        if not self.comparison_log:
            return {"message": "No comparisons logged"}
        
        return {
            "total_comparisons": len(self.comparison_log),
            "recent_comparisons": self.comparison_log[-10:]  # Last 10
        }
    
    def save_logs(self, output_file: Optional[str] = None):
        """Save logs to JSON file"""
        if output_file is None:
            output_file = f"logs/gap_assessment_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        log_data = {
            "index_usage": self.index_usage_log,
            "comparisons": self.comparison_log,
            "index_usage_summary": self.get_index_usage_summary(),
            "comparison_summary": self.get_comparison_summary()
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        self.logger.info(f"Logs saved to: {output_file}")
        return output_file

