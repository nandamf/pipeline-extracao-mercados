import logging

from scrapers.mix_mateus.client import (
    MixMateusClient
)
from scrapers.mix_mateus.constants import (
    DEFAULT_HITS_PER_PAGE
)
from scrapers.mix_mateus.parser import (
    MixMateusParser
)
from scrapers.base import BaseScraper


logger = logging.getLogger(__name__)


class MixMateusScraper(BaseScraper):

    def __init__(
        self,
        client=None,
        parser=None
    ):

        self.client = client or MixMateusClient()
        self.parser = parser or MixMateusParser()

    def search(
        self,
        search_term,
        cep=None,
        hits_per_page=DEFAULT_HITS_PER_PAGE,
        max_pages=None,
    ):

        records = []
        page = 0

        while True:

            raw_data = self.client.search(
                search_term=search_term,
                hits_per_page=hits_per_page,
                page=page
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
                "Mix Mateus page collected. page=%s records=%s total=%s",
                page + 1,
                len(page_records),
                len(records)
            )

            page += 1

            nb_pages = raw_data.get("nbPages")

            if nb_pages is not None and page >= nb_pages:
                break

            if max_pages is not None and page >= max_pages:
                break

        return records
