import unittest
import os
import sys

# Add root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from src.config import SecureString, SpaceLordConfig
from src.errors import ConfigurationError

class TestSecureString(unittest.TestCase):
    def test_basic_lifecycle(self):
        original = "super_secret_key"
        secure = SecureString(original)

        # 1. Check Obfuscation (Internal data != original bytes)
        self.assertNotEqual(secure._data, original.encode('utf-8'))

        # 2. Check Reveal
        self.assertEqual(secure.reveal(), original)

        # 3. Check Masking
        self.assertEqual(repr(secure), "<SecureString: ***HIDDEN***>")
        self.assertEqual(str(secure), "<SecureString: ***HIDDEN***>")

        # 4. Check Boolean Truthiness
        self.assertTrue(bool(secure))

    def test_empty(self):
        secure = SecureString("")
        self.assertEqual(secure.reveal(), "")
        self.assertFalse(bool(secure))
        self.assertEqual(repr(secure), "<SecureString: ***HIDDEN***>")

    def test_spacelord_config_integration(self):
        # The env var SpaceLordConfig.from_env() actually reads is `PRIVATE_KEY`
        # (see src/config.py:119). Earlier tests used `SPACELORD_PRIVATE_KEY`,
        # which was silently ignored — masking the developer's real .env value
        # bleeding through into the test.
        # The conftest autouse fixture clears PRIVATE_KEY/SPACELORD_PRIVATE_KEY/etc.
        # before every test, so this assignment is the only source of truth here.
        pk = "0x" + "a" * 64
        os.environ["PRIVATE_KEY"] = pk
        os.environ["SPACELORD_SIMULATE"] = "false"

        config = SpaceLordConfig.from_env()

        self.assertIsInstance(config.private_key, SecureString)
        self.assertEqual(config.private_key.reveal(), pk)

        try:
            config.validate()
        except ConfigurationError as e:
            self.fail(f"ConfigurationError raised: {e}")

    def test_spacelord_config_validation_failure(self):
        os.environ["PRIVATE_KEY"] = "invalid_key_too_short"
        os.environ["SPACELORD_SIMULATE"] = "false"

        config = SpaceLordConfig.from_env()

        with self.assertRaises(ConfigurationError):
            config.validate()

if __name__ == '__main__':
    unittest.main()
