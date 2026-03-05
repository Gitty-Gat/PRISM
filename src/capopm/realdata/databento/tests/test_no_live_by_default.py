import os
import unittest

from src.capopm.realdata.databento.transport import LiveTransport, TransportError


class TestNoLiveByDefault(unittest.TestCase):
    def test_live_transport_disabled_without_env(self):
        os.environ.pop("PRISM_DATABENTO_LIVE", None)
        with self.assertRaises(TransportError):
            LiveTransport(api_key="dummy")


if __name__ == "__main__":
    unittest.main()
