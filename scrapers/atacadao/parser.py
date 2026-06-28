from datetime import datetime, timezone

from scrapers.atacadao.constants import (
    MARKET_NAME,
    SOURCE_URL
)
from scrapers.base import BaseParser


class AtacadaoParser(BaseParser):

    def parse_products(
        self,
        raw_data,
        search_term=None,
        cep=None,
        collected_at=None
    ):

        collected_at = collected_at or datetime.now(timezone.utc)

        products = (
            raw_data.get("data", {})
            .get("search", {})
            .get("products", {})
        )

        records = []

        for edge in products.get("edges") or []:

            node = edge.get("node") or {}

            records.append(
                self.parse_product(
                    item=node,
                    search_term=search_term,
                    cep=cep,
                    collected_at=collected_at
                )
            )

        return records

    def parse_product(
        self,
        item,
        search_term=None,
        cep=None,
        collected_at=None
    ):

        offers = item.get("offers") or {}

        return self.build_product_record(
            market=MARKET_NAME,
            product_name=item.get("name"),
            price=offers.get("highPrice"),
            unit_price=offers.get("highPrice"),
            category=self._get_category(item),
            collected_at=collected_at,
            source_url=SOURCE_URL,
            search_term=search_term,
            cep=cep,
            source_product_id=item.get("id"),
            sku=item.get("sku"),
            ean=search_term,
            brand=(item.get("brand") or {}).get("name"),
            wholesale_price=offers.get("lowPrice"),
            image_url=self._get_image_url(item)
        )

    def _get_category(
        self,
        item
    ):

        breadcrumbs = (
            item.get("breadcrumbList", {})
            .get("itemListElement", [])
        )

        if len(breadcrumbs) < 2:
            return None

        return breadcrumbs[-2].get("name")

    def _get_image_url(
        self,
        item
    ):

        images = item.get("image") or []

        if not images:
            return None

        return images[0].get("url")
