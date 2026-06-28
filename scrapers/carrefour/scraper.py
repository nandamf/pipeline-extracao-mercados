import logging

from scrapers.base import BaseScraper
from scrapers.carrefour.client import (
    CarrefourClient
)
from scrapers.carrefour.parser import CarrefourParser


logger = logging.getLogger(__name__)


class CarrefourScraper(BaseScraper):

    def __init__(
        self,
        client=None,
        parser=None
    ):

        self.client = client or CarrefourClient()
        self.parser = parser or CarrefourParser()

    def search(
        self,
        search_term,
        cep=None,
        max_pages=None
    ):

        raw_html = self.client.search(
            search_term=search_term,
            cep=cep
        )

        records = self.parser.parse_products(
            raw_html=raw_html,
            search_term=search_term,
            cep=cep
        )

        logger.info(
            "Carrefour page collected. records=%s",
            len(records)
        )

        return records
