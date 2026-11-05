def clear_market(bids, asks):
    """Midpoint Double Auction Settlement in INR (₹2.50 - ₹6.00)."""
    sorted_asks = sorted(asks, key=lambda x: x["price"])
    sorted_bids = sorted(bids, key=lambda x: x["price"], reverse=True)

    cleared_trades = []

    for ask in sorted_asks:
        for bid in sorted_bids:
            if bid["volume"] > 0 and ask["volume"] > 0 and bid["price"] >= ask["price"]:
                matched_vol = min(bid["volume"], ask["volume"])
                cleared_price = round((bid["price"] + ask["price"]) / 2.0, 2)

                cleared_trades.append({
                    "seller_id": ask["id"],
                    "buyer_id": bid["id"],
                    "volume_kwh": round(matched_vol, 3),
                    "price_inr": cleared_price
                })

                bid["volume"] -= matched_vol
                ask["volume"] -= matched_vol

    return cleared_trades

GRID_BUY_TARIFF = 6.00    # Rs/kWh paid when importing from the main grid
GRID_SELL_TARIFF = 2.50   # Rs/kWh received when exporting to the main grid


def clear_slot(decisions):
    """Clear one market slot from several prosumers' decisions.

    decisions: list of dicts with id, e_tra_kw (+ sell / - buy) and bid_price.
    One slot is one hour, so kW and kWh are numerically equal.
    Uses clear_market() (midpoint double auction); anything left unmatched trades with the grid.
    """
    bids, asks = [], []
    for d in decisions:
        e, p = d["e_tra_kw"], d["bid_price"]
        if e > 0.001:
            asks.append({"id": d["id"], "volume": float(e), "price": float(p)})
        elif e < -0.001:
            bids.append({"id": d["id"], "volume": float(-e), "price": float(p)})

    trades = clear_market(bids, asks)           # mutates the remaining volumes in bids / asks
    p2p_kwh = sum(t["volume_kwh"] for t in trades)
    mcp = round(sum(t["volume_kwh"] * t["price_inr"] for t in trades) / p2p_kwh, 2) if p2p_kwh else None
    grid_import = sum(b["volume"] for b in bids)
    grid_export = sum(a["volume"] for a in asks)

    return {
        "trades": trades,
        "mcp": mcp,
        "p2p_kwh": round(p2p_kwh, 3),
        "grid_import_kwh": round(grid_import, 3),
        "grid_import_cost": round(grid_import * GRID_BUY_TARIFF, 2),
        "grid_export_kwh": round(grid_export, 3),
        "grid_export_revenue": round(grid_export * GRID_SELL_TARIFF, 2),
    }
