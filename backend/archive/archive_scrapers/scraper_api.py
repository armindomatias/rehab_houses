import requests

API_KEY = "0a5bb471a13282f10ff4ceb28d6eedcc"

def scraper_api(url : str = None):
    scrape_url = f"http://api.scraperapi.com?api_key={API_KEY}&url={url}&render=true&country_code=pt&premium=true"
    html = requests.get(scrape_url).text
    print(html)



if __name__ == '__main__':

    url = "https://www.idealista.pt/imovel/34082358/"

    scraper_api(url)