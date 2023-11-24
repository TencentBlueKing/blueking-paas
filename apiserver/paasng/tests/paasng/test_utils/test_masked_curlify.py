import json
from urllib.parse import parse_qs, quote

from requests import Request

import paasng.utils.masked_curlify as curlify
from paasng.utils.masked_curlify import MASKED_CONTENT


class TestToCurlMasked:
    def test_mask_query_params(self):
        test_request = Request("GET", "https://example.com/api?BK_PASSWORD=123456&api_key=abcdef")
        prepared_request = test_request.prepare()

        curlify.to_curl(prepared_request)

        assert f"BK_PASSWORD={quote(MASKED_CONTENT)}" in str(prepared_request.url)
        assert f"api_key={quote(MASKED_CONTENT)}" in str(prepared_request.url)

    def test_mask_json_data(self):
        test_request = Request("POST", "https://example.com/api", json={"BK_PASSWORD": "123456", "api_key": "abcdef"})
        prepared_request = test_request.prepare()

        curlify.to_curl(prepared_request)

        json_data = json.loads(prepared_request.body)  # type: ignore
        assert json_data["BK_PASSWORD"] == MASKED_CONTENT
        assert json_data["api_key"] == MASKED_CONTENT

    def test_mask_form_data(self):
        test_request = Request("POST", "https://example.com/api", data={"BK_PASSWORD": "123456", "api_key": "abcdef"})
        prepared_request = test_request.prepare()

        curlify.to_curl(prepared_request)

        form_data = parse_qs(prepared_request.body)  # type: ignore
        assert form_data["BK_PASSWORD"] == [MASKED_CONTENT]
        assert form_data["api_key"] == [MASKED_CONTENT]

    def test_mask_header_data(self):
        test_request = Request(
            "POST", "https://example.com/api", headers={"BK_PASSWORD": "123456", "api_key": "abcdef"}
        )
        prepared_request = test_request.prepare()

        curlify.to_curl(prepared_request)

        assert prepared_request.headers["BK_PASSWORD"] == MASKED_CONTENT
        assert prepared_request.headers["api_key"] == MASKED_CONTENT
