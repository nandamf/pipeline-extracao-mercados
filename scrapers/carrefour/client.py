import json

import requests
from playwright.sync_api import sync_playwright

from scrapers.carrefour.constants import (
    DEFAULT_TIMEOUT,
    HEADERS,
    SEARCH_URL
)


class CarrefourClient:

    def __init__(
        self,
        timeout=DEFAULT_TIMEOUT,
    ):

        self.timeout = timeout

    def search(
        self,
        search_term,
        cep=None
    ):

        url = SEARCH_URL.format(
            search_term=search_term
        )

        with sync_playwright() as playwright:

            browser = playwright.chromium.launch(
                headless=True
            )

            page = browser.new_page(
                extra_http_headers=HEADERS
            )

            try:

                page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=self.timeout * 1000
                )

                return page.content()

            finally:

                browser.close()

    def extract_ean(
        self,
        product_url
    ):

        try:

            from bs4 import BeautifulSoup

            response = requests.get(
                product_url,
                headers=HEADERS,
                timeout=self.timeout
            )

            response.raise_for_status()

            soup = BeautifulSoup(
                response.text,
                "html.parser"
            )

            script = soup.find(
                "script",
                {"type": "application/ld+json"}
            )

            if not script:
                return None

            data = json.loads(
                script.text
            )

            return data.get("gtin")

        except Exception:

            return None

    def extrair_ean(
        self,
        url_produto
    ):

        return self.extract_ean(
            product_url=url_produto
        )
