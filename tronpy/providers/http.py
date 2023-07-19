import os
import random
import sys
import time
from typing import Any, List, Union
from urllib.parse import urljoin

import requests

from tronpy.version import VERSION

DEFAULT_TIMEOUT = 10.0
DEFAULT_API_KEYS = [
    "999fb9e3-49f0-434d-9839-e2ef58a76d76"
]


class HTTPProvider:
    """An HTTP Provider for API request.

    :param endpoint_uri: HTTP API URL base. Default value is ``"https://api.trongrid.io/"``. Can also be configured via
        the ``TRONPY_HTTP_PROVIDER_URI`` environment variable.
    :param timeout: HTTP timeout in seconds.
    :param api_key: TronGRID API Key in str, or list of str.
    :param jw_token: TronGRID JWT Credentials in str.
    """

    def __init__(
        self,
        endpoint_uri: Union[str, dict] = None,
        timeout: float = DEFAULT_TIMEOUT,
        api_key: Union[str, List[str]] = None,
        jw_token: str = None,
    ):
        super().__init__()

        if endpoint_uri is None:
            self.endpoint_uri = os.environ.get("TRONPY_HTTP_PROVIDER_URI", "https://api.trongrid.io/")
        elif isinstance(endpoint_uri, (dict,)):
            self.endpoint_uri = endpoint_uri["fullnode"]
        elif isinstance(endpoint_uri, (str,)):
            self.endpoint_uri = endpoint_uri
        else:
            raise TypeError(f"unknown endpoint uri {endpoint_uri}")

        if "trongrid" in self.endpoint_uri:
            self.use_api_key = True
            if isinstance(api_key, (str,)):
                self._api_keys = [api_key]
            elif isinstance(api_key, (list,)) and api_key:
                self._api_keys = api_key
            else:
                self._api_keys = DEFAULT_API_KEYS.copy()

            self._default_api_keys = self._api_keys.copy()
        else:
            self.use_api_key = False
        self.jw_token = jw_token

        self.sess = requests.session()
        self.sess.headers["User-Agent"] = f"Tronpy/{VERSION}"

        self.timeout = timeout
        """Request timeout in second."""

    def make_request(self, method: str, params: Any = None) -> dict:
        if self.use_api_key:
            self.sess.headers["Tron-Pro-Api-Key"] = self.random_api_key

        if self.jw_token is not None:
            self.sess.headers["Authorization"] = f"Bearer {self.jw_token}"

        if params is None:
            params = {}
        url = urljoin(self.endpoint_uri, method)
        resp = self.sess.post(url, json=params, timeout=self.timeout)

        if self.use_api_key:
            if resp.status_code == 403 and b"Exceed the user daily usage" in resp.content:
                print("W:", resp.json().get("Error", "rate limit!"), file=sys.stderr)
                self._handle_rate_limit()
                return self.make_request(method, params)

        resp.raise_for_status()
        return resp.json()

    @property
    def random_api_key(self):
        return random.choice(self._api_keys)

    def _handle_rate_limit(self):
        if len(self._api_keys) > 1:
            self._api_keys.remove(self.sess.headers["Tron-Pro-Api-Key"])
        else:
            print("W: Please add as-many API-Keys in HTTPProvider", file=sys.stderr)
            time.sleep(0.9)
