from abc import ABC, abstractmethod


class BaseScraper(ABC):

    @abstractmethod
    def search(
        self,
        search_term,
        cep=None,
        max_pages=None
    ):
        raise NotImplementedError


class BaseParser:

    def build_product_record(
        self,
        market,
        product_name,
        price,
        unit_price,
        category,
        collected_at,
        source_url,
        search_term=None,
        cep=None,
        source_product_id=None,
        sku=None,
        ean=None,
        brand=None,
        wholesale_price=None,
        image_url=None
    ):

        searched_ean = self.get_searched_ean(
            search_term
        )
        ean, ean_source = self.resolve_ean(
            market=market,
            returned_ean=ean,
            searched_ean=searched_ean
        )

        return {
            "market": market,
            "product_name": str(product_name) if product_name is not None else None,
            "price": self.to_float(price),
            "unit_price": self.to_float(unit_price),
            "category": str(category) if category is not None else None,
            "collected_at": collected_at.isoformat(),
            "source_url": str(source_url) if source_url is not None else None,
            "search_term": str(search_term) if search_term is not None else None,
            "cep": str(cep) if cep is not None else None,
            "source_product_id": str(source_product_id) if source_product_id is not None else None,
            "sku": str(sku) if sku is not None else None,
            "ean": ean,
            "searched_ean": searched_ean,
            "ean_source": ean_source,
            "brand": str(brand) if brand is not None else None,
            "wholesale_price": self.to_float(wholesale_price),
            "image_url": str(image_url) if image_url is not None else None
        }

    def get_searched_ean(
        self,
        search_term
    ):

        if search_term is None:
            return None

        value = str(search_term).strip()

        if value.isdigit() and len(value) in (8, 12, 13, 14):
            return value

        return None

    def resolve_ean(
        self,
        market,
        returned_ean,
        searched_ean
    ):

        if market == "carrefour" and searched_ean:
            return searched_ean, "search_term"

        if returned_ean:
            return str(returned_ean), "market_response"

        if searched_ean:
            return searched_ean, "search_term"

        return None, None

    def to_float(
        self,
        value
    ):

        if value is None:
            return None

        try:
            return float(value)
        except (TypeError, ValueError):
            return None
