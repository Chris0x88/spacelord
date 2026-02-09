
import unittest
import os
import math
from pacman_config import PacmanConfig

class TestPacmanConfigSecurity(unittest.TestCase):
    def setUp(self):
        # Clear environment variables before each test
        for key in ["PACMAN_MAX_SWAP", "PACMAN_MAX_DAILY", "PACMAN_MAX_SLIPPAGE", "PACMAN_PRIVATE_KEY"]:
            if key in os.environ:
                del os.environ[key]

    def test_nan_handling(self):
        os.environ["PACMAN_MAX_SWAP"] = "nan"
        os.environ["PACMAN_MAX_DAILY"] = "nan"
        os.environ["PACMAN_MAX_SLIPPAGE"] = "nan"
        os.environ["PACMAN_PRIVATE_KEY"] = "0" * 64

        config = PacmanConfig.from_env()

        self.assertFalse(math.isnan(config.max_swap_amount_usd))
        self.assertFalse(math.isnan(config.max_daily_volume_usd))
        self.assertFalse(math.isnan(config.max_slippage_percent))

        self.assertEqual(config.max_swap_amount_usd, 1.00)
        self.assertEqual(config.max_daily_volume_usd, 10.00)
        self.assertEqual(config.max_slippage_percent, 1.0)

        valid, msg = config.validate()
        self.assertTrue(valid, msg)

    def test_inf_handling(self):
        os.environ["PACMAN_MAX_SWAP"] = "inf"
        os.environ["PACMAN_PRIVATE_KEY"] = "0" * 64

        config = PacmanConfig.from_env()

        # min(inf, 1.0) is 1.0, but our _safe_float also catches inf and returns default
        self.assertEqual(config.max_swap_amount_usd, 1.00)

    def test_invalid_float_handling(self):
        os.environ["PACMAN_MAX_SWAP"] = "not-a-float"
        os.environ["PACMAN_PRIVATE_KEY"] = "0" * 64

        config = PacmanConfig.from_env()
        self.assertEqual(config.max_swap_amount_usd, 1.00)

    def test_negative_value_validation(self):
        os.environ["PACMAN_MAX_SWAP"] = "-0.5"
        os.environ["PACMAN_PRIVATE_KEY"] = "0" * 64

        config = PacmanConfig.from_env()
        self.assertEqual(config.max_swap_amount_usd, -0.5)

        valid, msg = config.validate()
        self.assertFalse(valid)
        self.assertIn("Invalid max_swap_amount_usd", msg)

    def test_hard_cap_enforcement(self):
        os.environ["PACMAN_MAX_SWAP"] = "5.0" # Above $1.00 hard cap
        os.environ["PACMAN_PRIVATE_KEY"] = "0" * 64

        config = PacmanConfig.from_env()
        # Should be capped at 1.00 by the min(max_swap, 1.00) logic
        self.assertEqual(config.max_swap_amount_usd, 1.00)

if __name__ == "__main__":
    unittest.main()
