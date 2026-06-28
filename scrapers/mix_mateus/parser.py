from datetime import datetime, timezone

from scrapers.base import BaseParser
from scrapers.mix_mateus.constants import (
    MARKET_NAME,
    SOURCE_URL
)


class MixMateusParser(BaseParser):

    def parse_products(
        self,
        raw_data,
        search_term=None,
        cep=None,
        collected_at=None
    ):

        collected_at = collected_at or datetime.now(timezone.utc)
        records = []

        for item in raw_data.get("hits") or []:

            records.append(
                self.parse_product(
                    item=item,
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

        price = self.to_float(
            item.get("sale_price")
        )

        return self.build_product_record(
            market=MARKET_NAME,
            product_name=item.get("name"),
            price=price,
            unit_price=price,
            category=item.get("category"),
            collected_at=collected_at,
            source_url=SOURCE_URL,
            search_term=search_term,
            cep=cep,
            source_product_id=item.get("objectID"),
            sku=item.get("sku"),
            ean=item.get("barcode"),
            brand=item.get("brand"),
            wholesale_price=item.get("wholesale_sale_price"),
            image_url=item.get("image")
        )
