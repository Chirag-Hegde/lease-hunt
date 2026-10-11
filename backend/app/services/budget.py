"""Per-run token/dollar budget. Agents abort gracefully (partial results)
when the budget is exceeded."""

from dataclasses import dataclass, field


class BudgetExceededError(Exception):
    def __init__(self, spent_usd: float, budget_usd: float, tokens: int, budget_tokens: int):
        self.spent_usd = spent_usd
        self.budget_usd = budget_usd
        super().__init__(
            f"run budget exceeded: ${spent_usd:.4f} of ${budget_usd:.2f}, "
            f"{tokens} of {budget_tokens} tokens"
        )


@dataclass
class BudgetTracker:
    budget_usd: float
    budget_tokens: int
    spent_usd: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0
    _exceeded: bool = field(default=False, repr=False)

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out

    @property
    def exceeded(self) -> bool:
        return self._exceeded

    def add(self, tokens_in: int, tokens_out: int, cost_usd: float) -> None:
        """Record usage, then raise if this pushed the run over budget."""
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        self.spent_usd += cost_usd
        if self.spent_usd > self.budget_usd or self.total_tokens > self.budget_tokens:
            self._exceeded = True
            raise BudgetExceededError(
                self.spent_usd, self.budget_usd, self.total_tokens, self.budget_tokens
            )
