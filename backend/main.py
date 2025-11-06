from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from src.apify_idealista_scraper import ApifyIdealistaScraper


# Data model for request
class AnalyzeRequest(BaseModel):
    link: str

app = FastAPI()

# Allow frontend (vite) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # your React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
def analyze_property(link: AnalyzeRequest):
    # Here you put your actual logic: renovation cost, rent estimate etc.
    # For now, just a fake response:

    print(link)

    fake_response = {
        "link": link,
        "renovation_cost": 25000,
        "monthly_rent_estimate": 1200,
        "roi": "8%"
    }

    return fake_response

# print('Put your idealista listing here:')
# url = input()

# scraper = ApifyIdealistaScraper()

# single_result = scraper.scrape_single(url_listing=url)
