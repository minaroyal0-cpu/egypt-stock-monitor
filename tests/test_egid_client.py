import json
import unittest
from unittest.mock import patch

from src.egid_client import EGIDError, fetch_delayed_feed


class FakeResponse:
    status = 200
    headers = {"Content-Type": "application/json; charset=utf-8"}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"items":[{"symbol":"ABUK","close":42.5}]}'


class EGIDClientTests(unittest.TestCase):
    def test_requires_vendor_issued_token(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(EGIDError, "missing_EGID_BEARER_TOKEN"):
                fetch_delayed_feed("/api/DelayedFeed/getEGXMarketWatch")

    def test_rejects_unlisted_routes(self):
        with self.assertRaisesRegex(ValueError, "unsupported_egid_endpoint"):
            fetch_delayed_feed("/api/Feed/anything", token="test")

    def test_uses_fixed_egid_host_and_bearer_auth(self):
        seen = {}

        def fake_open(request, timeout):
            seen["url"] = request.full_url
            seen["auth"] = request.get_header("Authorization")
            seen["timeout"] = timeout
            return FakeResponse()

        result = fetch_delayed_feed(
            "/api/DelayedFeed/getEGXMarketWatch",
            params={"marketId": 1},
            token="vendor-token",
            timeout=7,
            opener=fake_open,
        )
        self.assertTrue(seen["url"].startswith("https://ticker.egidegypt.com/"))
        self.assertEqual(seen["auth"], "Bearer vendor-token")
        self.assertEqual(seen["timeout"], 7)
        self.assertEqual(result["raw"]["items"][0]["symbol"], "ABUK")
        self.assertEqual(result["normalization_status"], "not_normalized")
        self.assertEqual(result["feed_type"], "delayed")

    def test_rejects_non_json_response(self):
        class NonJson(FakeResponse):
            headers = {"Content-Type": "text/html"}

        with self.assertRaisesRegex(EGIDError, "egid_non_json_response"):
            fetch_delayed_feed(
                "/api/DelayedFeed/getEGXMarketWatch",
                token="vendor-token",
                opener=lambda request, timeout: NonJson(),
            )

    def test_rejects_invalid_json(self):
        class BadJson(FakeResponse):
            def read(self):
                return b"not json"

        with self.assertRaisesRegex(EGIDError, "egid_invalid_json"):
            fetch_delayed_feed(
                "/api/DelayedFeed/getEGXMarketWatch",
                token="vendor-token",
                opener=lambda request, timeout: BadJson(),
            )


if __name__ == "__main__":
    unittest.main()
