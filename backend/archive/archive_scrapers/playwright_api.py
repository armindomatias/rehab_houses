from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re, json
import os

# Scrape data
def scrape(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # try visible mode
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = context.new_page()
        page.goto(url)

        # simulate activity
        page.mouse.move(100, 100)
        page.wait_for_timeout(2000)  # wait 2s

        html = page.content()
        browser.close()

        return html 

# 
def select_html(html):

    soup = BeautifulSoup(html, "lxml")
    
    title = soup.select_one("span.main-info__title-main")
    price = soup.select_one("span.info-data-price")
    location = soup.select_one("span.main-info__title-minor")
    description = soup.select_one("div.comment")
    #features = [li.get_text(strip=True) for li in soup.select(".details-property li")]

    # coords = None
    # match = re.search(r'"latitude":([0-9\.\-]+).*?"longitude":([0-9\.\-]+)', html)
    # if match:
    #     coords = {"lat": match.group(1), "lng": match.group(2)}

    data = {
        "title": title.get_text(strip=True) if title else None,
        "price": price.get_text(strip=True) if price else None,
        "location": location.get_text(strip=True) if location else None,
        "description": description.get_text(strip=True) if description else None,
        #"features": features,
        #"coords": coords
    }

    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    
    url = "https://www.idealista.pt/imovel/34082358/"
    url = "https://www.idealista.pt/imovel/34170709/"
    
    html = scrape(url=url)
    select_html(html=html)