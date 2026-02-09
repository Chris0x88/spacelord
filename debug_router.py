from pacman_variant_router import PacmanVariantRouter

router = PacmanVariantRouter()
router.load_pools()

# Test direct swap step
step = router.find_swap_step("HBAR", "USDC")

from pacman_price_manager import price_manager
print(f"DEBUG SCRIPT: HBAR Price: {price_manager.get_hbar_price()}")

if step:

    print(f"Found Step: {step.from_token} -> {step.to_token}")
    print(f"  Fee Percent: {step.fee_percent}")
    print(f"  Fee Percent * 100: {step.fee_percent * 100}")
    if step.details:
        print(f"  Details Fee BPS: {step.details.get('fee_bps')}")
else:
    print("No step found")
