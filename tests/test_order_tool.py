from src.tools.order_tool import OrderLookupTool, normalize_order_id, extract_order_id


def test_order_id_normalization():
    assert normalize_order_id("ord-1007") == "ORD-1007"
    assert normalize_order_id("  ORD-1007  ") == "ORD-1007"
    assert extract_order_id("Where is ord-1007 please?") == "ORD-1007"
    assert extract_order_id("Please check ORD-1004") == "ORD-1004"


def test_valid_order_lookup_privacy():
    tool = OrderLookupTool()
    res = tool.lookup("ORD-1007")
    
    assert res.found is True
    assert res.order_id == "ORD-1007"
    assert res.status == "shipped"
    assert res.carrier == "UPS"
    assert res.estimated_delivery == "2026-08-22"
    assert res.handoff_recommended is False
    
    # PRIVACY SANITY CHECK: Ensure sensitive fields are not in model attributes
    d = res.model_dump()
    assert "email" not in d
    assert "address" not in d
    assert "risk_score" not in d
    assert "warehouse_note" not in d


def test_cancelled_order_stale_eta_suppression():
    tool = OrderLookupTool()
    res = tool.lookup("ORD-1004")
    
    assert res.found is True
    assert res.status == "cancelled"
    # Stale carrier and ETA must be suppressed
    assert res.estimated_delivery is None
    assert res.carrier is None
    assert res.tracking_number is None
    assert "cancelled" in res.customer_safe_message.lower()


def test_shipped_without_eta():
    tool = OrderLookupTool()
    res = tool.lookup("ORD-1011")
    
    assert res.found is True
    assert res.status == "shipped"
    assert res.carrier == "Canada Post"
    assert res.estimated_delivery is None


def test_unknown_order():
    tool = OrderLookupTool()
    res = tool.lookup("ORD-9999")
    
    assert res.found is False
    assert res.handoff_recommended is True
    assert "could not be found" in res.message.lower()


def test_missing_order_id():
    tool = OrderLookupTool()
    res = tool.lookup("")
    
    assert res.found is False
    assert "missing" in res.message.lower()


def test_order_exception():
    tool = OrderLookupTool()
    res = tool.lookup("ORD-1010")
    
    assert res.found is True
    assert res.status == "exception"
    assert res.handoff_recommended is True
