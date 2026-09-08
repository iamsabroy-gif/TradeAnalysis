"""
Review Queue Store for Phase 1 Gatekeeper.
Maps strictly to implementpdf.md Stage 5 and Phase1-WebApp-Implementation-Plan.md §5.4.
Manages persistent review queue items resulting from low confidence, near-threshold escalation, or discrepancies.
"""

from typing import Any, Dict, List, Optional
from backend.app.models.schemas import ReviewQueueItem


class ReviewStore:
    """Store for managing manual review queue items."""

    def __init__(self):
        self._items: Dict[str, ReviewQueueItem] = {}

    def add_items(self, items: List[ReviewQueueItem]) -> None:
        for item in items:
            self._items[item.id] = item

    def get_item(self, item_id: str) -> Optional[ReviewQueueItem]:
        return self._items.get(item_id)

    def list_for_ticker(self, ticker: str) -> List[ReviewQueueItem]:
        clean = ticker.strip().upper()
        return [item for item in self._items.values() if item.ticker == clean]

    def list_all(self) -> List[ReviewQueueItem]:
        return list(self._items.values())

    def resolve(self, item_id: str, resolved_value: Any, reviewer: str = "analyst") -> Optional[ReviewQueueItem]:
        item = self._items.get(item_id)
        if not item:
            return None
        # Once resolved, remove from pending queue
        del self._items[item_id]
        return item


# Global review store instance
review_store = ReviewStore()
