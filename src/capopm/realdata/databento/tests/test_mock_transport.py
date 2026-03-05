import unittest

from src.capopm.realdata.databento.transport import MockTransport, HttpResponse, TransportError


class TestMockTransport(unittest.TestCase):
    def test_missing_fixture_raises(self):
        t = MockTransport()
        with self.assertRaises(TransportError):
            t.post_form("https://example.com", {"a": "1"}, basic_auth=True)

    def test_fixture_returns(self):
        resp = HttpResponse(status=200, headers={}, body=b"1.0")
        key = ("https://example.com", (("a", "1"),))
        t = MockTransport({key: resp})
        out = t.post_form("https://example.com", {"a": "1"}, basic_auth=True)
        self.assertEqual(out.status, 200)
        self.assertEqual(out.body, b"1.0")


if __name__ == "__main__":
    unittest.main()
