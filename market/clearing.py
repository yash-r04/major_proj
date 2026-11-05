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
