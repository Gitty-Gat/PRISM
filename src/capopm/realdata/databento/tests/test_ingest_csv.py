import unittest

from src.capopm.realdata.databento.ingest import parse_trades_csv


class TestIngestCSV(unittest.TestCase):
    def test_parse_trades_csv(self):
        body = b"ts_event,price,size,side,trade_id,instrument_id\n1700000000000000000,100.0,5,BUY,t1,TEST\n"
        evs = list(parse_trades_csv(body))
        self.assertEqual(len(evs), 1)
        ev = evs[0]
        self.assertEqual(ev.event_type, "TRADE")
        self.assertEqual(ev.instrument_id, "TEST")
        self.assertEqual(ev.size, 5.0)
        self.assertEqual(ev.side, "BUY")


if __name__ == "__main__":
    unittest.main()
