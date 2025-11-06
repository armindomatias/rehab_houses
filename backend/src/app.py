from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.apify_idealista_scraper import ApifyIdealistaScraper


# Data model for request validation
# This defines the structure of the JSON body that the frontend sends
class AnalyzeRequest(BaseModel):
    """Request model for property analysis."""
    link: str

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

# Analyze property
@app.post("/analyze")
def analyze_property(request: AnalyzeRequest):
    """Analyze a property from an Idealista link."""
    # TODO: Replace with actual analysis logic
    return {
        "link": request.link,
        "renovation_cost": 25000,
        "monthly_rent_estimate": 1200,
        "roi": "8%"
    }
