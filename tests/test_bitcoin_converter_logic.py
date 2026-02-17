import unittest
from unittest.mock import MagicMock, patch
from src.bitcoin_converter import UniversalSwapper, WBTC_EVM_ADDR, WBTC_LEGACY_ID, WBTC_NATIVE_ID

class TestBitcoinConverter(unittest.TestCase):
    def setUp(self):
        self.mock_w3 = MagicMock()
        self.mock_account = "0x1234567890123456789012345678901234567890"
        self.swapper = UniversalSwapper(self.mock_w3, self.mock_account, "0xkey")

        # Mock contracts
        self.mock_hts_precompile = MagicMock()
        self.swapper.hts_precompile = self.mock_hts_precompile

        # Mock generic contract getter
        self.mock_contract = MagicMock()
        self.swapper._get_contract = MagicMock(return_value=self.mock_contract)

        # Mock transaction sender to just return a receipt
        self.swapper._send_transaction = MagicMock(return_value={'status': 1})

    def test_is_hts_precompile(self):
        # Valid HTS Long-Zero
        self.assertTrue(self.swapper.is_hts_precompile("0x0000000000000000000000000000000000000123"))
        # Standard EVM
        self.assertFalse(self.swapper.is_hts_precompile("0xd7d4d91d64a6061fa00a94e2b3a2d2a5fb677849"))
        # WBTC EVM
        self.assertFalse(self.swapper.is_hts_precompile(WBTC_EVM_ADDR))

    def test_convert_evm_to_hts(self):
        print("\n--- Test EVM -> HTS ---")
        token_in = WBTC_EVM_ADDR
        token_out = WBTC_NATIVE_ID # 0.0.10082597
        amount = 1000
        # Valid dummy address
        spender = "0x0000000000000000000000000000000000000111"

        # Mock allowance to be 0 (trigger approve)
        self.mock_contract.functions.allowance.return_value.call.return_value = 0

        # Mock isAssociated to be False (trigger associate) for Output
        self.mock_hts_precompile.functions.isAssociated.return_value.call.return_value = False

        self.swapper.convert(token_in, token_out, amount, spender)

        # VERIFY OUTPUT (HTS):
        # Should call associateToken on HTS precompile for token_out
        self.mock_hts_precompile.functions.associateToken.assert_called_with(self.swapper._ensure_evm_address(token_out))

    def test_convert_hts_to_evm(self):
        print("\n--- Test HTS -> EVM ---")
        token_in = WBTC_LEGACY_ID
        token_out = WBTC_EVM_ADDR
        amount = 1000
        # Valid dummy address
        spender = "0x0000000000000000000000000000000000000111"

        # Mock allowance 0
        self.mock_contract.functions.allowance.return_value.call.return_value = 0

        # Mock isAssociated False for Input HTS
        self.mock_hts_precompile.functions.isAssociated.return_value.call.return_value = False

        self.swapper.convert(token_in, token_out, amount, spender)

        # VERIFY INPUT (HTS):
        # Should call associateToken for token_in
        self.mock_hts_precompile.functions.associateToken.assert_any_call(self.swapper._ensure_evm_address(token_in))

        # Should call approve (ERC20 style)
        self.mock_contract.functions.approve.assert_called()

        # VERIFY OUTPUT (EVM):
        # Should NOT call associateToken for token_out
        try:
            self.mock_hts_precompile.functions.associateToken.assert_called_with(WBTC_EVM_ADDR)
            self.fail("Should not associate EVM address")
        except AssertionError:
            pass # Expected

if __name__ == '__main__':
    unittest.main()
