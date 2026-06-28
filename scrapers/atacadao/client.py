import json

from scrapers.atacadao.constants import (
    COUNTRY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_PAGE_SIZE,
    DEFAULT_TIMEOUT,
    LOCALE,
    REGION_URL,
    SALES_CHANNEL,
    SEARCH_URL
)
from scrapers.http_client import HttpJsonClient


class AtacadaoClient(HttpJsonClient):

    def __init__(
        self,
        timeout=DEFAULT_TIMEOUT,
        max_retries=DEFAULT_MAX_RETRIES
    ):

        super().__init__(
            timeout=timeout,
            max_retries=max_retries
        )

    def get_region(
        self,
        cep
    ):

        data = self.request_json(
            method="GET",
            url=REGION_URL,
            params={
                "postalCode": cep,
                "sc": 2,
                "country": COUNTRY
            }
        )

        return {
            "region_id": data[0]["id"],
            "seller_id": data[0]["sellers"][0]["id"]
        }

    def search(
        self,
        search_term,
        region_id,
        seller_id,
        offset=0,
        limit=DEFAULT_PAGE_SIZE
    ):

        variables = {
            "first": limit,
            "after": str(offset),
            "sort": "score_desc",
            "term": search_term,
            "selectedFacets": [
                {
                    "key": "region-id",
                    "value": region_id
                },
                {
                    "key": "channel",
                    "value": json.dumps({
                        "salesChannel": SALES_CHANNEL,
                        "seller": seller_id,
                        "regionId": region_id
                    })
                },
                {
                    "key": "locale",
                    "value": LOCALE
                }
            ]
        }

        return self.request_json(
            method="GET",
            url=SEARCH_URL,
            params={
                "operationName": "ProductsQuery",
                "variables": json.dumps(variables)
            }
        )
