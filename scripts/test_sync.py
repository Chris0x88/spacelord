import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from src.controller import PacmanController
from src.plugins.power_law.bot import PowerLawBot
from src.config import PacmanConfig

print("--- Testing Purpose-Based Auto-Provisioning ---")

# 1. Clear ROBOT_ACCOUNT_ID from env and file
PacmanConfig.set_env_value("ROBOT_ACCOUNT_ID", "")
print("Cleared ROBOT_ACCOUNT_ID from .env")

# 2. Initialize Controller
app = PacmanController()

# 3. Initialize Bot
# This should trigger _ensure_robot_account -> create_sub_account(purpose="rebalancer")
bot = PowerLawBot(app)

# 4. Verification
robot_id = app.config.robot_account_id
print(f"Robot ID after initialization: {robot_id}")

env_content = Path(".env").read_text()
if robot_id and f"ROBOT_ACCOUNT_ID='{robot_id}'" in env_content:
    print("✅ SUCCESS: Bot auto-provisioned its account and updated .env!")
else:
    # Try alternate check for dotenv quoting
    if robot_id and f"ROBOT_ACCOUNT_ID={robot_id}" in env_content:
        print("✅ SUCCESS: Bot auto-provisioned its account and updated .env!")
    else:
        print(f"❌ FAILURE: .env was not updated correctly. Content: {env_content}")

# 5. Check Nickname in Registry
import json
with open("data/accounts.json") as f:
    accounts = json.load(f)
    found = False
    for a in accounts:
        if a.get("id") == robot_id and a.get("nickname") == "Bitcoin Rebalancer Daemon":
            found = True
            break
    if found:
        print(f"✅ SUCCESS: Account {robot_id} has correct nickname in registry!")
    else:
        print(f"❌ FAILURE: Nickname not found in registry for {robot_id}.")
