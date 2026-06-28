import logging

from scrapers.atacadao.client import AtacadaoClient
from scrapers.atacadao.constants import DEFAULT_PAGE_SIZE
from scrapers.atacadao.parser import AtacadaoParser
from scrapers.base import BaseScraper


logger = logging.getLogger(__name__)


class AtacadaoScraper(BaseScraper):

    def __init__(
        self,
        client=None,
        parser=None
    ):

        self.client = client or AtacadaoClient()
        self.parser = parser or AtacadaoParser()

    def search(
        self,
        search_term,
        cep=None,
        page_size=DEFAULT_PAGE_SIZE,
        max_pages=None
    ):

        if not cep:
            raise ValueError("Atacadao scraper requires a CEP.")

        region = self.client.get_region(cep)

        offset = 0
        page = 0
        records = []

        while True:

            raw_data = self.client.search(
                search_term=search_term,
                region_id=region["region_id"],
                seller_id=region["seller_id"],
                offset=offset,
                limit=page_size
            )

            page_records = self.parser.parse_products(
                raw_data=raw_data,
                search_term=search_term,
                cep=cep
            )

            if not page_records:
                break

            records.extend(page_records)

            logger.info(
                "Atacadao page collected. page=%s records=%s total=%s",
                page + 1,
                len(page_records),
                len(records)
            )

            page += 1
            offset += page_size

            if max_pages is not None and page >= max_pages:
                break

        return records
