from src.apify_idealista_scraper import ApifyIdealistaScraper

print('Put your idealista listing here:')
url = input()

scraper = ApifyIdealistaScraper()

single_result = scraper.scrape_single(url_listing=url)
