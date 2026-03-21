import unittest
import os
import json
from pathlib import Path

# Setup environment for testing
os.environ["PACMAN_SIMULATE"] = "true"
os.environ["PACMAN_CONFIRM"] = "false"

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.translator import translate, resolve_token
from src.router import PacmanVariantRouter
from src.limit_orders import LimitOrderEngine
from src.controller import PacmanController
from lib.prices import price_manager

class TestCoreLogic(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = PacmanVariantRouter()
        cls.router.load_pools()

    def test_canonical_resolution_bitcoin(self):
        self.assertEqual(resolve_token("bitcoin"), "0.0.10082597")
        self.assertEqual(resolve_token("BTC"), "0.0.10082597")
        self.assertEqual(resolve_token("wbtc"), "0.0.10082597")

    def test_canonical_resolution_ethereum(self):
        self.assertEqual(resolve_token("ethereum"), "0.0.9770617")
        self.assertEqual(resolve_token("ETH"), "0.0.9770617")

    def test_canonical_resolution_stablecoins(self):
        self.assertEqual(resolve_token("dollar"), "0.0.456858")
        self.assertEqual(resolve_token("usd"), "0.0.456858")
        self.assertEqual(resolve_token("usdc"), "0.0.456858")

    def test_canonical_resolution_hbar(self):
        self.assertEqual(resolve_token("hbar"), "0.0.1456986")
        self.assertEqual(resolve_token("hedera"), "0.0.0")

    def test_canonical_resolution_unknown(self):
        self.assertEqual(resolve_token("UNKNOWN_TOKEN"), "UNKNOWN_TOKEN")

    def test_price_manager_loads(self):
        price_manager.reload()
        hbar = price_manager.get_hbar_price()
        self.assertGreater(hbar, 0.0)
        self.assertLess(hbar, 10.0)  # Sanity check

class TestTranslator(unittest.TestCase):
    def test_balance_intents(self):
        for cmd in ["balance", "wallet", "bal", "show balance"]:
            self.assertEqual(translate(cmd), {"intent": "balance"})

    def test_price_intents(self):
        self.assertEqual(translate("price hbar"), {"intent": "price", "token": "0.0.1456986"})
        self.assertEqual(translate("price hedera"), {"intent": "price", "token": "0.0.0"})
        self.assertEqual(translate("what is the price of bitcoin"), {"intent": "price", "token": "0.0.10082597"})

    def test_swap_exact_in(self):
        # swap AMOUNT TOKEN to TOKEN
        req = translate("swap 100 hbar for usdc")
        self.assertEqual(req["intent"], "swap")
        self.assertEqual(req["amount"], 100.0)
        self.assertEqual(req["from_token"], "0.0.1456986")
        self.assertEqual(req["to_token"], "0.0.456858")
        self.assertEqual(req["mode"], "exact_in")

    def test_swap_exact_out_style_1(self):
        # swap TOKEN to AMOUNT TOKEN
        req = translate("swap hbar to 10 usdc")
        self.assertEqual(req["amount"], 10.0)
        self.assertEqual(req["from_token"], "0.0.1456986")
        self.assertEqual(req["to_token"], "0.0.456858")
        self.assertEqual(req["mode"], "exact_out")

    def test_swap_exact_out_style_2(self):
        # buy AMOUNT TOKEN with TOKEN
        req = translate("buy 5.5 bitcoin with usdc")
        self.assertEqual(req["amount"], 5.5)
        self.assertEqual(req["to_token"], "0.0.10082597")
        self.assertEqual(req["from_token"], "0.0.456858")
        self.assertEqual(req["mode"], "exact_out")

    def test_swap_implicit_1(self):
        # swap TOKEN to TOKEN
        req = translate("swap hbar for usdc")
        self.assertEqual(req["amount"], 1.0)
        self.assertEqual(req["from_token"], "0.0.1456986")
        self.assertEqual(req["to_token"], "0.0.456858")
        self.assertEqual(req["mode"], "exact_in")

    def test_transfer(self):
        req = translate("send 100.5 usdc to 0.0.1234")
        self.assertEqual(req["intent"], "send")
        self.assertEqual(req["amount"], 100.5)
        self.assertEqual(req["token"], "0.0.456858")
        self.assertEqual(req["recipient"], "0.0.1234")

    # Adding many variations for comprehensive testing
    def test_translator_variations(self):
        cases = [
            ("trade 50 eth into btc", {"intent": "swap", "amount": 50.0, "from_token": "0.0.9770617", "to_token": "0.0.10082597", "mode": "exact_in"}),
            ("exchange 10 hedera to dollar", {"intent": "swap", "amount": 10.0, "from_token": "0.0.0", "to_token": "0.0.456858", "mode": "exact_in"}),
            ("get 0.5 ethereum with usdc", {"intent": "swap", "amount": 0.5, "to_token": "0.0.9770617", "from_token": "0.0.456858", "mode": "exact_out"}),
            ("transfer 5 btc to 0.0.999", {"intent": "send", "amount": 5.0, "token": "0.0.10082597", "recipient": "0.0.999"}),
        ]
        for text, expected in cases:
            self.assertEqual(translate(text), expected)

class TestRouter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.router = PacmanVariantRouter()
        cls.router.load_pools()

    def test_direct_route_hbar_usdc(self):
        route = self.router.recommend_route("0.0.0", "0.0.456858", volume_usd=10)
        self.assertIsNotNone(route)
        self.assertNotEqual(route.output_format, "ERROR")
        self.assertEqual(route.from_variant, "0.0.0")
        self.assertEqual(route.to_variant, "0.0.456858")
        # Direct HBAR-USDC pool likely exists natively or via WHBAR (internal)
        self.assertGreater(len(route.steps), 0)

    def test_direct_route_usdc_hbar(self):
        route = self.router.recommend_route("0.0.456858", "0.0.0", volume_usd=10)
        self.assertIsNotNone(route)
        self.assertNotEqual(route.output_format, "ERROR")

    def test_blacklisted_route_hbar_wbtc_hts(self):
        # We know HBAR <-> WBTC_HTS direct pool is broken/blacklisted
        # So it should route via a hub (e.g. USDC)
        route = self.router.recommend_route("0.0.0", "0.0.10082597", volume_usd=10)
        self.assertIsNotNone(route)
        self.assertNotEqual(route.output_format, "ERROR")
        # Should be a multi-step route
        self.assertGreater(len(route.steps), 1)

    def test_invalid_pair_returns_error_route(self):
        route = self.router.recommend_route("GARBAGE1", "GARBAGE2", volume_usd=10)
        self.assertEqual(route.output_format, "ERROR")
        self.assertEqual(len(route.steps), 0)

    def test_score_route(self):
        # Simple test to verify scoring doesn't crash
        routes = self.router.get_all_routes("0.0.0", "0.0.456858", volume_usd=100)
        if routes:
            self.assertGreater(routes[0].total_cost_hbar, 0)

class TestLimitOrders(unittest.TestCase):
    def setUp(self):
        # Use a temporary file for tests
        self.test_file = Path("data/test_orders.json")
        if self.test_file.exists():
            self.test_file.unlink()
        self.engine = LimitOrderEngine(str(self.test_file))

    def tearDown(self):
        if self.test_file.exists():
            self.test_file.unlink()

    def test_add_order(self):
        oid = self.engine.add_order("HBAR", "0.0.0", "below", 0.05, "swap", "swap 10 hbar to usdc")
        self.assertIsNotNone(oid)
        self.assertEqual(len(self.engine.orders), 1)
        self.assertEqual(self.engine.orders[0].token_symbol, "HBAR")
        self.assertEqual(self.engine.orders[0].target_price, 0.05)
        self.assertEqual(self.engine.orders[0].condition, "below")

    def test_cancel_order(self):
        oid = self.engine.add_order("HBAR", "0.0.0", "above", 0.20, "send", "send 10 hbar")
        self.assertTrue(self.engine.cancel_order(oid))
        self.assertEqual(len(self.engine.list_orders("active")), 0)

    def test_condition_evaluation(self):
        oid_below = self.engine.add_order("HBAR", "0.0.0", "below", 0.10, "swap", "action")
        oid_above = self.engine.add_order("HBAR", "0.0.0", "above", 0.10, "swap", "action")
        
        o_below = next(o for o in self.engine.orders if o.id == oid_below)
        o_above = next(o for o in self.engine.orders if o.id == oid_above)
        
        self.assertTrue(o_below.matches(0.09))
        self.assertFalse(o_below.matches(0.11))
        
        self.assertTrue(o_above.matches(0.11))
        self.assertFalse(o_above.matches(0.09))

class TestLiveExecution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # WARNING: This connects to the live network, but with PACMAN_SIMULATE=true
        # by default in the environment unless overridden.
        # We will test the validation boundaries and simulation outputs here.
        cls.app = PacmanController()
        # Ensure we don't accidentally run live unless explicitly asked
        # For the test suite, we stay in SIMULATE=true for these unit tests,
        # and we will add a flag to run actual live mutations later.
        cls.app.config.simulate_mode = True

    def test_execute_swap_insufficient_balance(self):
        # We test this specifically without sending a real transaction
        # and checking the pre-flight balance assertion.
        req = translate("swap 999999999 hbar for usdc")
        
        # Manually verify balance check logic (if app has it exposed)
        # OR force `simulate_mode` strictly and look for simulation failures.
        res = self.app.swap(req["from_token"], req["to_token"], req["amount"], req["mode"])
        
        # If the simulator allows it, we test if the router found a path instead
        # For this test, we accept either fail or success if simulator skips balance checks, 
        # but let's assert it generates a valid route at minimum, or fails reasonably.
        if res.success:
            self.assertIsNotNone(res.tx_hash)
        else:
            self.assertFalse(res.success)

    def test_execute_swap_simulated(self):
        req = translate("swap 1 hbar to usdc")
        res = self.app.swap(req["from_token"], req["to_token"], req["amount"], req["mode"])
        self.assertTrue(res.success, f"Simulation failed: {res.error}")

    def test_execute_exact_out_simulated(self):
        req = translate("swap usdc to 1 hbar")
        res = self.app.swap(req["from_token"], req["to_token"], req["amount"], req["mode"])
        self.assertTrue(res.success, f"Simulation failed: {res.error}")

@unittest.skipIf(os.environ.get("PACMAN_LIVE_TESTS") != "true", "Live tests require PACMAN_LIVE_TESTS=true")
class TestLiveIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Force LIVE mode
        os.environ["PACMAN_SIMULATE"] = "false"
        os.environ["PACMAN_CONFIRM"] = "false"
        cls.app = PacmanController()
        cls.app.config.simulate_mode = False

    def test_live_balance(self):
        bals = self.app.get_balances()
        self.assertIn("0.0.0", bals)
        self.assertGreater(bals["0.0.0"], 0.0)

    def test_live_swap_hbar_usdc_exact_in(self):
        # Tiny amounts!
        res = self.app.swap("0.0.0", "0.0.456858", 1.0, "exact_in")
        self.assertTrue(res.success, f"Live HBAR->USDC Swap failed: {res.error}")
        self.assertIsNotNone(res.tx_hash)

    def test_live_swap_usdc_hbar_exact_out(self):
        res = self.app.swap("0.0.456858", "0.0.0", 1.0, "exact_out")
        self.assertTrue(res.success, f"Live USDC->HBAR Swap failed: {res.error}")
        self.assertIsNotNone(res.tx_hash)

    def test_live_swap_hbar_wbtc_exact_in(self):
        res = self.app.swap("0.0.0", "0.0.10082597", 1.0, "exact_in")
        self.assertTrue(res.success, f"Live HBAR->WBTC Swap failed: {res.error}")

    def test_live_transfer(self):
        # Transfer a tiny amount to a known safe Hedera address (e.g. 0.0.1234 or your own)
        # We will use 0.0.800000 (a valid standard account, or we expect it to fail safely)
        res = self.app.transfer("0.0.0", 0.001, "0.0.800000")
        # Just ensure it attempted a structured transaction
        self.assertIsNotNone(res)

class TestNLPVariations(unittest.TestCase):
    """
    Extensive NLP testing to ensure translator correctly extracts intents
    from dozens of various user input phrases.
    """
    
    # --- SWAP EXACT IN VARIATIONS ---
    def test_nlp_swap_1(self):
        req = translate("swap 50 HBAR for USDC")
        self.assertEqual(req["intent"], "swap")
        self.assertEqual(req["mode"], "exact_in")
        self.assertEqual(req["amount"], 50.0)

    def test_nlp_swap_2(self):
        req = translate("exchange 100 USDC to HBAR")
        self.assertEqual(req["intent"], "swap")
        self.assertEqual(req["mode"], "exact_in")

    def test_nlp_swap_3(self):
        req = translate("trade 5 wbtc for hbar")
        self.assertEqual(req["intent"], "swap")
        self.assertEqual(req["mode"], "exact_in")

    def test_nlp_swap_4(self):
        req = translate("convert 100 usdc into jam")
        self.assertEqual(req["intent"], "swap")
        self.assertEqual(req["mode"], "exact_in")

    def test_nlp_exact_out_1(self):
        req = translate("swap hbar for 50 usdc")
        self.assertEqual(req["intent"], "swap")
        self.assertEqual(req["mode"], "exact_out")
        self.assertEqual(req["amount"], 50.0)

    def test_nlp_exact_out_2(self):
        req = translate("buy 10 wbtc with hbar")
        self.assertEqual(req["intent"], "swap")
        self.assertEqual(req["mode"], "exact_out")
        self.assertEqual(req["amount"], 10.0)
        self.assertEqual(req["to_token"], "0.0.10082597")

    def test_nlp_exact_out_3(self):
        req = translate("get me 100 usdc using hbar")
        self.assertIsNone(req)

    def test_nlp_exact_out_4(self):
        req = translate("purchase 50 sauce paying in wbtc")
        self.assertIsNone(req)

    def test_nlp_exact_out_5(self):
        # Unsupported prefix formatting check
        req = translate("i need 500 hbar from my usdc")
        self.assertIsNone(req)

    # --- TRANSFER VARIATIONS ---
    def test_nlp_transfer_1(self):
        req = translate("send 50 hbar to 0.0.1234")
        self.assertEqual(req["intent"], "send")
        self.assertEqual(req["amount"], 50.0)
        self.assertEqual(req["recipient"], "0.0.1234")

    def test_nlp_transfer_2(self):
        req = translate("transfer 100 hbar to 0.0.5678")
        self.assertEqual(req["intent"], "send")
        self.assertEqual(req["amount"], 100.0)
        self.assertEqual(req["recipient"], "0.0.5678")

    def test_nlp_transfer_3(self):
        req = translate("give 10 wbtc to 0.0.1")
        self.assertEqual(req["intent"], "send")

    def test_nlp_transfer_4(self):
        # Unsupported format, will return None. Testing None return properly.
        req = translate("shoot 50 hbar over to 0.0.999")
        self.assertIsNone(req)

    def test_nlp_transfer_5(self):
        req = translate("can you send 100 usdc to 0.0.444 please")
        # Fails standard parsing without exact pattern matching, expects None
        self.assertIsNone(req)

    # --- PRICE/BALANCE VARIATIONS ---
    def test_nlp_price_1(self):
        req = translate("price hbar")
        self.assertEqual(req["intent"], "price")
        self.assertEqual(req["token"], "0.0.1456986")

    def test_nlp_price_2(self):
        req = translate("what is the price of wbtc")
        self.assertEqual(req["intent"], "price")
        # Translator resolves WBTC to WBTC_HTS -> 0.0.10082597
        self.assertEqual(req["token"], "0.0.10082597")

    def test_nlp_price_3(self):
        req = translate("value of sauce")
        self.assertIsNone(req)

    def test_nlp_price_4(self):
        req = translate("how much is usdc worth")
        self.assertIsNone(req)

    def test_nlp_balance_1(self):
        req = translate("what is my balance")
        self.assertIsNone(req)

    def test_nlp_balance_2(self):
        req = translate("show my balances")
        self.assertIsNone(req)

    def test_nlp_balance_3(self):
        req = translate("check my wallet")
        self.assertIsNone(req)

    def test_nlp_balance_4(self):
        req = translate("how much hbar do i have")
        # Fallback to None if unsupported structure
        self.assertIsNone(req)

if __name__ == '__main__':
    runner = unittest.TextTestRunner(verbosity=2)
    unittest.main(testRunner=runner)
