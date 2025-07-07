import time
import json
import logging
import re
from playwright.sync_api import sync_playwright, TimeoutError
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BASE_URL = "https://www.mcdonalds.com"
FULL_MENU_URL = f"{BASE_URL}/ua/uk-ua/eat/fullmenu.html"
OUTPUT_FILE = "mcdonalds_data.json"

NUTRITION_MAP = {
    'calories': ['калорійність', 'calories'],
    'fats': ['жири', 'fat'],
    'carbs': ['вуглеводи', 'carbs', 'carbohydrates'],
    'proteins': ['білки', 'protein'],
    'unsaturated_fats': ['нжк', 'saturated fat'],
    'sugar': ['цукор', 'sugars'],
    'salt': ['сіль', 'sodium'],
    'portion': ['порція', 'serving size']
}


def find_key_by_text(text_to_find, mapping_dict):
    text_to_find = text_to_find.lower().strip().replace(':', '')
    for key, possible_names in mapping_dict.items():
        if text_to_find in possible_names:
            return key
    return None


def get_product_links(page):
    logging.info(f"Navigating to the main menu page: {FULL_MENU_URL}")
    try:
        page.goto(FULL_MENU_URL, timeout=60000, wait_until='networkidle')

        logging.info("Scrolling page to load all dynamic content...")
        for i in range(5):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            logging.debug(f"Scroll attempt {i + 1} completed.")
            time.sleep(1)

        page.wait_for_selector('.cmp-category__item-link', timeout=30000)
        soup = BeautifulSoup(page.content(), 'html.parser')

        link_tags = soup.find_all('a', class_='cmp-category__item-link')
        product_links = set()
        for tag in link_tags:
            href = tag.get('href')
            if href:
                full_url = BASE_URL + href if href.startswith('/') else href
                product_links.add(full_url)

        logging.info(f"Successfully found {len(product_links)} unique product links.")
        return list(product_links)
    except Exception as e:
        logging.error(f"Could not retrieve product links from {FULL_MENU_URL}. Error: {e}", exc_info=True)
        return []


def parse_product_page(page, url):
    logging.info(f"Parsing product page: {url}")
    try:
        page.goto(url, timeout=45000, wait_until='domcontentloaded')
        page.wait_for_selector('div.cmp-product-details-main__desktop-only', timeout=15000)

        try:
            nutrition_button_selector = "button.cmp-accordion__button[aria-controls]"
            page.wait_for_selector(nutrition_button_selector, timeout=10000)
            page.click(nutrition_button_selector)
            logging.debug("Clicked the nutrition accordion button.")
            page.wait_for_selector(
                '.cmp-accordion__panel[aria-hidden="false"] .primarynutritions li',
                state='visible',
                timeout=7000
            )
            logging.debug("Nutrition content is visible.")
            time.sleep(0.1)

        except TimeoutError:
            logging.warning(
                f"Nutrition accordion not found, failed to open, or content did not load in time on page: {url}.")
        except Exception as e:
            logging.error(f"An unexpected error occurred while expanding the nutrition accordion on {url}. Error: {e}",
                          exc_info=True)

        soup = BeautifulSoup(page.content(), 'html.parser')
        data = {"url": url}

        data['name'] = soup.select_one('h1.cmp-product-details-main__heading').get_text(strip=True) if soup.select_one(
            'h1.cmp-product-details-main__heading') else None
        logging.debug(f"  Parsed name: {data['name']}")

        data['description'] = soup.select_one('div.cmp-product-details-main__description div.cmp-text').get_text(
            strip=True) if soup.select_one('div.cmp-product-details-main__description div.cmp-text') else None
        logging.debug(f"  Parsed description: {data['description']}")

        for key in NUTRITION_MAP:
            data[key] = None

        panel_content = soup.select_one('.cmp-accordion__panel[aria-hidden="false"]')
        if not panel_content:
            logging.warning(
                f"Could not find the expanded nutrition panel on page: {url}. Nutrition data will be missing.")
            return data

        primary_rows = panel_content.select('div.primarynutritions li.cmp-nutrition-summary__heading-primary-item')
        for row in primary_rows:
            metric_span = row.find('span', class_='metric')
            value_span = row.find('span', class_='value')
            if not (metric_span and value_span):
                continue

            label_el = metric_span.find('span', {'aria-hidden': 'true'}, class_=lambda c: c != 'sr-only')
            value_el = value_span.find('span', {'aria-hidden': 'true'}, class_=lambda c: c != 'sr-only')
            if not (label_el and value_el):
                continue

            raw_label = label_el.get_text(strip=True)
            raw_value = value_el.get_text(strip=True)

            if raw_value.strip().lower().startswith('n/a'):
                final_value = raw_value.strip()
            else:
                label, percentage = raw_label, ""
                match = re.search(r"(.+?)\s*\((.+)\)", raw_label)
                if match:
                    label = match.group(1).strip()
                    percentage = f"({match.group(2).strip()})"
                value = raw_value.split('/')[0].strip()
                final_value = f"{value} {percentage}".strip()

            data_key = find_key_by_text(raw_label.split('(')[0], NUTRITION_MAP)

            if data_key:
                data[data_key] = final_value
                logging.debug(f"  Parsed {data_key}: {final_value}")

        secondary_rows = panel_content.select(
            'div.secondarynutritions div.cmp-nutrition-summary__details-column-view-desktop li.label-item')
        for row in secondary_rows:
            metric_span = row.find('span', class_='metric')
            value_span = row.find('span', class_='value')
            if not (metric_span and value_span):
                continue

            label = metric_span.get_text(strip=True).replace(':', '')
            value_el = value_span.find('span', {'aria-hidden': 'true'})
            if not value_el:
                continue

            final_value = value_el.get_text(strip=True, separator='\n').split('\n')[0]

            data_key = find_key_by_text(label, NUTRITION_MAP)

            if data_key:
                data[data_key] = final_value
                logging.debug(f"  Parsed {data_key}: {final_value}")

        return data

    except Exception as e:
        logging.error(f"Failed to parse page {url}. An unexpected error occurred: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    logging.info("Scraper initiated.")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        product_urls = get_product_links(page)
        all_products_data = []

        if product_urls:
            total = len(product_urls)
            logging.info(f"Starting to process {total} product pages.")
            for i, url in enumerate(product_urls):
                logging.info(f"[{i + 1}/{total}] Processing URL: {url}")
                product_info = parse_product_page(page, url)
                if product_info:
                    all_products_data.append(product_info)
                time.sleep(0.5)

            if all_products_data:
                with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
                    json.dump(all_products_data, f, ensure_ascii=False, indent=4)
                logging.info(f"Scraping complete. Saved {len(all_products_data)} products to {OUTPUT_FILE}")
            else:
                logging.warning("Scraping finished, but no data was collected or saved.")
        else:
            logging.error("No product URLs were found. Cannot proceed with scraping.")

        browser.close()
    logging.info("Scraper has finished execution.")