import unittest

from src.capopm.realdata.databento.cost_guard import require_budget_ok, BudgetExceeded


class TestCostGuard(unittest.TestCase):
    def test_budget_ok(self):
        require_budget_ok(0.0)
        require_budget_ok(1.99)

    def test_budget_exceeded(self):
        with self.assertRaises(BudgetExceeded):
            require_budget_ok(2.01)


if __name__ == "__main__":
    unittest.main()
