"""
API endpoint for Gap Assessment Agent
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import uvicorn

from agent.gap_assessment_agent import GapAssessmentAgent


app = FastAPI(title="Gap Assessment API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AssessmentRequest(BaseModel):
    """Request model for gap assessment"""
    query: str
    force_extraction: Optional[bool] = False


class AssessmentResponse(BaseModel):
    """Response model for gap assessment"""
    status: str
    query: str
    assessment: Dict[str, Any]
    message: Optional[str] = None


# Initialize agent (singleton)
_agent: Optional[GapAssessmentAgent] = None


def get_agent() -> GapAssessmentAgent:
    """Get or create agent instance"""
    global _agent
    if _agent is None:
        _agent = GapAssessmentAgent()
    return _agent


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Gap Assessment API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    try:
        agent = get_agent()
        return {
            "status": "healthy",
            "agent_initialized": agent is not None
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.post("/assess", response_model=AssessmentResponse)
async def assess_gaps(request: AssessmentRequest):
    """
    Perform gap assessment
    
    Args:
        request: Assessment request with query and optional force_extraction flag
        
    Returns:
        Gap assessment results in a clean, structured format
    """
    try:
        agent = get_agent()
        result = agent.assess_gaps(
            query=request.query,
            force_extraction=request.force_extraction
        )
        
        # Extract and format assessment
        assessment_data = result.get("assessment", {})
        
        # Format response with parsed gaps
        formatted_assessment = {
            "gaps": assessment_data.get("gaps", []),
            "summary": assessment_data.get("summary", {
                "total_gaps": 0,
                "critical_gaps": 0,
                "high_priority_gaps": 0,
                "overall_risk_score": 0
            })
        }
        
        # Add metrics if available
        if "metrics" in result:
            formatted_assessment["metrics"] = {
                "llm_calls": result["metrics"].get("llm_calls", 0),
                "latency_seconds": round(result["metrics"].get("latency_seconds", 0), 2),
                "search_results_count": result["metrics"].get("search_results_count", 0),
                "comparison_count": result["metrics"].get("comparison_count", 0)
            }
        
        return AssessmentResponse(
            status="success",
            query=request.query,
            assessment=formatted_assessment,
            message="Gap assessment completed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status")
async def get_status():
    """Get agent status and extraction dates"""
    try:
        agent = get_agent()
        status = agent.extraction_tool.get_extraction_status()
        return {
            "status": "success",
            "extraction_status": status,
            "available_indexes": agent.vector_db.list_indexes()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/logs/summary")
async def get_logs_summary():
    """Get logging summary"""
    try:
        agent = get_agent()
        return {
            "status": "success",
            "index_usage_summary": agent.logger.get_index_usage_summary(),
            "comparison_summary": agent.logger.get_comparison_summary()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

