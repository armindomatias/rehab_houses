from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.pipeline import PropertyAnalysisPipeline
from typing import Optional, Dict, Any


# Data model for request validation
# This defines the structure of the JSON body that the frontend sends
class AnalyzeRequest(BaseModel):
    """Request model for property analysis."""
    link: str
    options: Optional[Dict[str, Any]] = None

# Initialize FastAPI
app = FastAPI()

# Allow frontend (Next.js) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add a simple health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

# Initialize pipeline (can be reused across requests)
pipeline = PropertyAnalysisPipeline()

# Analyze property
@app.post("/analyze")
async def analyze_property(request: AnalyzeRequest):
    """
    Analyze a property from an Idealista link.
    
    Runs the complete pipeline:
    1. Scrape property data
    2. Extract gallery URLs
    3. Classify images
    4. Deduplicate classifications
    5. Calculate remodeling costs
    6. Calculate financial metrics
    """
    try:
        result = await pipeline.analyze(request.link, request.options)
        
        if not result.get('success'):
            raise HTTPException(
                status_code=500,
                detail=result.get('error', 'Pipeline execution failed')
            )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error analyzing property: {str(e)}"
        )
