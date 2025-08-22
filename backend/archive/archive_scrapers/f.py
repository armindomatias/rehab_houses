from playwright.sync_api import sync_playwright

url = "https://www.idealista.pt/imovel/34082358/"  # example listing

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=50)
    page = browser.new_page()

    # Simulate a real user
    page.set_extra_http_headers({
        "Accept-Language": "pt-PT,pt;q=0.9,en;q=0.8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                      " AppleWebKit/537.36 (KHTML, like Gecko)"
                      " Chrome/115.0.0.0 Safari/537.36"
    })

    page.goto(url, timeout=60000)
    
    # Wait for something more general first
    page.wait_for_selector("article.detail-info", timeout=60000)

    html = page.content()
    print(html[:1000])  # preview

    browser.close()
