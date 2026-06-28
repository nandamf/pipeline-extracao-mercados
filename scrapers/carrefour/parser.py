import html
import re
from datetime import datetime, timezone
from urllib.parse import urljoin

from scrapers.base import BaseParser
from scrapers.carrefour.constants import (
    MARKET_NAME,
    SOURCE_URL
)


class CarrefourParser(BaseParser):

    def parse_products(
        self,
        raw_html,
        search_term=None,
        cep=None,
        collected_at=None
    ):

        collected_at = collected_at or datetime.now(timezone.utc)
        records = []

        for card_html in self._find_product_cards(raw_html):

            record = self.parse_product(
                card_html=card_html,
                search_term=search_term,
                cep=cep,
                collected_at=collected_at
            )

            if record:
                records.append(record)

        return records

    def parse_product(
        self,
        card_html,
        search_term=None,
        cep=None,
        collected_at=None
    ):

        href = self._extract_attr(
            card_html,
            "href"
        )
        product_name = (
            self._extract_h2_text(card_html)
            or self._extract_attr(card_html, "alt")
        )
        image_url = self._extract_attr(
            card_html,
            "src"
        )
        price = self._extract_price(
            card_html
        )

        if not product_name and price is None:
            return None

        return self.build_product_record(
            market=MARKET_NAME,
            product_name=product_name,
            price=price,
            unit_price=price,
            category=None,
            collected_at=collected_at,
            source_url=urljoin(SOURCE_URL, href or ""),
            search_term=search_term,
            cep=cep,
            source_product_id=self._extract_source_product_id(href),
            sku=None,
            ean=None,
            brand=None,
            wholesale_price=None,
            image_url=image_url
        )

    def _find_product_cards(
        self,
        raw_html
    ):

        pattern = (
            r'<a\b[^>]*data-testid="search-product-card"'
            r'[^>]*>.*?</a>'
        )

        return re.findall(
            pattern,
            raw_html,
            flags=re.DOTALL
        )

    def _extract_attr(
        self,
        content,
        attr_name
    ):

        match = re.search(
            rf'{attr_name}="([^"]+)"',
            content
        )

        if not match:
            return None

        return html.unescape(
            match.group(1)
        )

    def _extract_h2_text(
        self,
        content
    ):

        match = re.search(
            r"<h2\b[^>]*>(.*?)</h2>",
            content,
            flags=re.DOTALL
        )

        if not match:
            return None

        return self._clean_text(
            match.group(1)
        )

    def _extract_price(
        self,
        content
    ):

        match = re.search(
            r'<span\b[^>]*class="[^"]*text-price-default[^"]*"[^>]*>'
            r"(.*?)</span>",
            content,
            flags=re.DOTALL
        )

        if not match:
            return None

        text = self._clean_text(
            match.group(1)
        )

        return self._parse_brl_price(
            text
        )

    def _parse_brl_price(
        self,
        value
    ):

        if not value:
            return None

        value = (
            value.replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )

        return self.to_float(value)

    def _extract_source_product_id(
        self,
        href
    ):

        if not href:
            return None

        match = re.search(
            r"-(\d+)(?:\?|$)",
            href
        )

        if not match:
            return None

        return match.group(1)

    def _clean_text(
        self,
        value
    ):

        value = re.sub(
            r"<[^>]+>",
            "",
            value
        )

        return html.unescape(
            value
        ).strip()
