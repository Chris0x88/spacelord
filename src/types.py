from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

class SwapStrategy(Enum):
    """
    Consumer-Friendly Swap Strategy.
    Maps to exactInput / exactOutput technically.
    """
    SPEND_EXACT = auto()   # "I want to spend exactly X" (exactInput)
    RECEIVE_EXACT = auto() # "I want to receive exactly X" (exactOutput)

    def __str__(self):
        if self == SwapStrategy.SPEND_EXACT:
            return "Spend Exact"
        return "Receive Exact"

@dataclass
class SwapIntent:
    """
    The Golden Record for a Swap Operation.
    This is the single source of truth passed between the Brain, CLI, and Engine.
    """
    token_in: Optional[str] = None  # Symbol e.g. "USDC"
    token_out: Optional[str] = None # Symbol e.g. "HBAR"
    qty: float = 0.0
    strategy: SwapStrategy = SwapStrategy.SPEND_EXACT # Default to "Spend Exact" as it's safer/more common

    @property
    def is_complete(self) -> bool:
        """Check if all necessary fields are populated."""
        return bool(self.token_in and self.token_out and self.qty > 0)

    def __str__(self):
        mode_str = "SPENDING" if self.strategy == SwapStrategy.SPEND_EXACT else "RECEIVING"
        return f"Intent: {mode_str} {self.qty} {self.token_in if self.strategy == SwapStrategy.SPEND_EXACT else self.token_out} -> {self.token_out if self.strategy == SwapStrategy.SPEND_EXACT else self.token_in}"
