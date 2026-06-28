from urllib.parse import urlencode

from scrapers.http_client import HttpJsonClient
from scrapers.mix_mateus.constants import (
    DEFAULT_HITS_PER_PAGE,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    HEADERS,
    SEARCH_URL
)


class MixMateusClient(HttpJsonClient):

    def __init__(
        self,
        timeout=DEFAULT_TIMEOUT,
        max_retries=DEFAULT_MAX_RETRIES
    ):

        super().__init__(
            timeout=timeout,
            max_retries=max_retries
        )

    def search(
        self,
        search_term,
        hits_per_page=DEFAULT_HITS_PER_PAGE,
        page=0
    ):

        params = urlencode({
            "query": search_term,
            "hitsPerPage": hits_per_page,
            "page": page
        })

        payload = {
            "params": params
        }

        return self.request_json(
            method="POST",
            url=SEARCH_URL,
            headers=HEADERS,
            json=payload
        )
