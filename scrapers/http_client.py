import logging
import time

import requests


logger = logging.getLogger(__name__)


class HttpJsonClient:

    def __init__(
        self,
        timeout=30,
        max_retries=3
    ):

        self.timeout = timeout
        self.max_retries = max_retries

    def request_json(
        self,
        method,
        url,
        headers=None,
        params=None,
        json=None
    ):

        last_error = None

        for attempt in range(1, self.max_retries + 1):

            try:

                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    json=json,
                    timeout=self.timeout
                )

                response.raise_for_status()

                return response.json()

            except requests.RequestException as error:

                last_error = error

                logger.warning(
                    "HTTP request failed. method=%s url=%s attempt=%s/%s error=%s",
                    method,
                    url,
                    attempt,
                    self.max_retries,
                    error
                )

                if attempt < self.max_retries:
                    time.sleep(attempt)

        raise RuntimeError(
            f"HTTP request failed after {self.max_retries} attempts"
        ) from last_error

    def request_text(
        self,
        method,
        url,
        headers=None,
        params=None
    ):

        last_error = None

        for attempt in range(1, self.max_retries + 1):

            try:

                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    timeout=self.timeout
                )

                response.raise_for_status()

                return response.text

            except requests.RequestException as error:

                last_error = error

                logger.warning(
                    "HTTP request failed. method=%s url=%s attempt=%s/%s error=%s",
                    method,
                    url,
                    attempt,
                    self.max_retries,
                    error
                )

                if attempt < self.max_retries:
                    time.sleep(attempt)

        raise RuntimeError(
            f"HTTP request failed after {self.max_retries} attempts"
        ) from last_error
