import unittest

from src.capopm.realdata.databento.schemas import TimeseriesRequest
from src.capopm.realdata.databento.validation import validate_request, RequestValidationError


class TestValidation(unittest.TestCase):
    def test_reject_bad_schema(self):
        req = TimeseriesRequest(dataset="GLBX.MDP3", schema="bad", symbols="ES.FUT", start="2024-01-03T14:30")  # type: ignore[arg-type]
        with self.assertRaises(RequestValidationError):
            validate_request(req, encoding="csv", compression="none")

    def test_reject_bad_timestamps(self):
        req = TimeseriesRequest(dataset="GLBX.MDP3", schema="trades", symbols="ES.FUT", start="2024/01/03", end="x")
        with self.assertRaises(RequestValidationError):
            validate_request(req, encoding="csv", compression="none")

    def test_accept_probe_shape(self):
        req = TimeseriesRequest(
            dataset="GLBX.MDP3",
            schema="trades",
            symbols="ES.FUT",
            stype_in="parent",
            stype_out="instrument_id",
            start="2024-01-03T14:30",
            end="2024-01-03T14:31",
        )
        validate_request(req, encoding="csv", compression="none")


if __name__ == "__main__":
    unittest.main()
