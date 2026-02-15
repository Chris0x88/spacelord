import unittest
import os
import sys

# Add root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/../")

from pacman_config import SecureString, PacmanConfig
from pacman_errors import ConfigurationError

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

    def test_pacman_config_integration(self):
        # Setup Env
        pk = "0x" + "a" * 64
        os.environ["PACMAN_PRIVATE_KEY"] = pk
        os.environ["PACMAN_SIMULATE"] = "false"

        # Load
        config = PacmanConfig.from_env()

        # Verify type and value
        self.assertIsInstance(config.private_key, SecureString)
        self.assertEqual(config.private_key.reveal(), pk)

        # Verify validation passes
        try:
            config.validate()
        except ConfigurationError as e:
            self.fail(f"ConfigurationError raised: {e}")

    def test_pacman_config_validation_failure(self):
        # Setup Invalid Env
        os.environ["PACMAN_PRIVATE_KEY"] = "invalid_key_too_short"
        os.environ["PACMAN_SIMULATE"] = "false"

        config = PacmanConfig.from_env()

        with self.assertRaises(ConfigurationError):
            config.validate()

if __name__ == '__main__':
    unittest.main()
