import json
import re
from pathlib import Path
from typing import Optional, Dict, Any
from src.config import ORDERS_FILE
from src.models import OrderResult, OrderItem


def normalize_order_id(raw_id: str) -> str:
    """Normalizes order ID by stripping whitespace and converting to uppercase."""
    return raw_id.strip().upper()


def extract_order_id(text: str) -> Optional[str]:
    """Extracts an order ID like ORD-1007 from user text."""
    match = re.search(r"\b(ORD-\d{4})\b", text, re.IGNORECASE)
    if match:
        return normalize_order_id(match.group(1))
    return None


class OrderLookupTool:
    """Deterministic order status lookup tool accessing data/orders.json."""
    
    def __init__(self, orders_filepath: Path = ORDERS_FILE):
        self.orders_filepath = orders_filepath
        self._load_dataset()

    def _load_dataset(self):
        with open(self.orders_filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.snapshot_at = data.get("snapshot_at")
        self.orders_map: Dict[str, Dict[str, Any]] = {
            order["order_id"]: order for order in data.get("orders", [])
        }

    def lookup(self, raw_order_id: Optional[str]) -> OrderResult:
        """
        Executes order status lookup for a given order ID.
        Applies privacy filtering, status precedence, and stale field removal.
        """
        if not raw_order_id or not raw_order_id.strip():
            return OrderResult(
                found=False,
                order_id="",
                status="unknown",
                message="Order ID is missing. Please provide a valid order ID (e.g., ORD-1007).",
                handoff_recommended=False,
            )

        norm_id = normalize_order_id(raw_order_id)
        order_data = self.orders_map.get(norm_id)

        if not order_data:
            return OrderResult(
                found=False,
                order_id=norm_id,
                status="unknown",
                message=f"Order '{norm_id}' could not be found. Please verify your order ID or contact support.",
                handoff_recommended=True,
            )

        status = order_data.get("status", "unknown")
        items = [
            OrderItem(
                sku=it.get("sku"),
                name=it.get("name"),
                quantity=it.get("quantity", 1),
                final_sale=it.get("final_sale", False),
            )
            for it in order_data.get("items", [])
        ]

        carrier = order_data.get("carrier")
        tracking_number = order_data.get("tracking_number")
        estimated_delivery = order_data.get("estimated_delivery")
        customer_safe_msg = order_data.get("customer_safe_message")

        handoff = False

        # Status Precedence & Stale Field Protection
        if status == "cancelled":
            carrier = None
            tracking_number = None
            estimated_delivery = None
            customer_safe_msg = "The order was cancelled and will not be shipped."
        elif status == "returned":
            estimated_delivery = None
            customer_safe_msg = "The return was received and processed."
        elif status == "shipped" and not estimated_delivery:
            customer_safe_msg = (
                f"The order has shipped with {carrier or 'the carrier'}. "
                "A delivery estimate is currently unavailable."
            )
        elif status == "exception":
            handoff = True
            customer_safe_msg = (
                "The shipment has an exception that requires support review."
            )

        # STRICT PRIVACY SANITIZATION:
        # Note: customer PII (name, email, shipping_address) and internal dict (risk_score, warehouse_note, tags)
        # are completely omitted from OrderResult.

        return OrderResult(
            found=True,
            order_id=norm_id,
            membership_tier=order_data.get("membership_tier"),
            items=items,
            placed_at=order_data.get("placed_at"),
            status=status,
            status_updated_at=order_data.get("status_updated_at"),
            shipped_at=order_data.get("shipped_at"),
            delivered_at=order_data.get("delivered_at"),
            carrier=carrier,
            tracking_number=tracking_number,
            estimated_delivery=estimated_delivery,
            customer_safe_message=customer_safe_msg,
            handoff_recommended=handoff,
        )
