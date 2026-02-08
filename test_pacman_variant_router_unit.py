import pytest
from pacman_variant_router import PacmanVariantRouter, RouteStep

def test_find_swap_step_success():
    """Test find_swap_step when a direct swap exists."""
    router = PacmanVariantRouter()
    # Mock the pool_graph
    # (token_in, token_out) -> (pool_id, fee_bps)
    router.pool_graph = {
        ("USDC", "WBTC[hts]"): ("pool123", 1500)
    }

    step = router.find_swap_step("USDC", "WBTC[hts]")

    assert step is not None
    assert isinstance(step, RouteStep)
    assert step.step_type == "swap"
    assert step.from_token == "USDC"
    assert step.to_token == "WBTC[hts]"
    assert step.fee_percent == 0.15  # 1500 / 10000
    assert step.details["pool_id"] == "pool123"
    assert step.details["fee_bps"] == 1500

def test_find_swap_step_not_found():
    """Test find_swap_step when no direct swap exists."""
    router = PacmanVariantRouter()
    router.pool_graph = {
        ("USDC", "WBTC[hts]"): ("pool123", 1500)
    }

    # Try a pair that isn't in the graph
    step = router.find_swap_step("USDC", "WETH[hts]")

    assert step is None

def test_find_swap_step_different_fee():
    """Test find_swap_step with a different fee tier."""
    router = PacmanVariantRouter()
    router.pool_graph = {
        ("USDC", "USDC[hts]"): ("pool456", 500)
    }

    step = router.find_swap_step("USDC", "USDC[hts]")

    assert step is not None
    assert step.fee_percent == 0.05  # 500 / 10000
    assert step.details["fee_bps"] == 500

def test_find_swap_step_case_sensitivity():
    """Test if find_swap_step is case sensitive (it should be based on current impl)."""
    router = PacmanVariantRouter()
    router.pool_graph = {
        ("USDC", "WBTC[hts]"): ("pool123", 1500)
    }

    # Symbols should match exactly
    step = router.find_swap_step("usdc", "WBTC[hts]")
    assert step is None
