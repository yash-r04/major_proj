import os
import json

def clear_market(bids: list, grid_buy_tariff: float = 6.00, grid_sell_tariff: float = 2.50) -> dict:
    """
    Clears a multi-prosumer energy market for a single time slot using a Pay-as-Bid double auction.
    
    bids: List of decision dicts output by inference.py / decide()
    grid_buy_tariff: Cost per kWh when buying from upstream main grid (INR)
    grid_sell_tariff: Price per kWh when selling excess back to main grid (INR)
    """
    sellers = []
    buyers = []
    
    # 1. Separate prosumers into sellers (+e_tra_kw) and buyers (-e_tra_kw)
    for bid in bids:
        e_tra = bid.get("e_tra_kw", 0.0)
        price = bid.get("bid_price", 4.00)
        prosumer_id = bid.get("id", "unknown")
        
        if e_tra > 0:
            sellers.append({"id": prosumer_id, "volume": e_tra, "price": price})
        elif e_tra < 0:
            buyers.append({"id": prosumer_id, "volume": abs(e_tra), "price": price})

    # 2. Sort sellers ascending by price (cheapest first) and buyers descending (highest willingness to pay)
    sellers.sort(key=lambda x: x["price"])
    buyers.sort(key=lambda x: x["price"], reverse=True)
    
    total_supply = sum(s["volume"] for s in sellers)
    total_demand = sum(b["volume"] for b in buyers)
    
    cleared_trades = []
    matched_volume = 0.0
    
    # 3. Double Auction Order Matching Loop
    s_idx = 0
    b_idx = 0
    
    while s_idx < len(sellers) and b_idx < len(buyers):
        seller = sellers[s_idx]
        buyer = buyers[b_idx]
        
        # Trade occurs only if buyer price >= seller price (or baseline clearing window)
        trade_vol = min(seller["volume"], buyer["volume"])
        
        if trade_vol > 0.001:
            # Pay-as-Bid / Midpoint clearing price formula (Zhang et al.)
            trade_price = round((seller["price"] + buyer["price"]) / 2.0, 2)
            
            cleared_trades.append({
                "seller_id": seller["id"],
                "buyer_id": buyer["id"],
                "volume_kw": round(trade_vol, 2),
                "cleared_price": trade_price,
                "total_cost": round(trade_vol * trade_price, 2)
            })
            
            matched_volume += trade_vol
            seller["volume"] -= trade_vol
            buyer["volume"] -= trade_vol
            
        if seller["volume"] <= 0.001:
            s_idx += 1
        if buyer["volume"] <= 0.001:
            b_idx += 1

    # 4. Handle Unmatched Imbalances with Upstream Grid Retailer
    unmatched_supply = sum(s["volume"] for s in sellers[s_idx:])
    unmatched_demand = sum(b["volume"] for b in buyers[b_idx:])
    
    # Calculate Market Clearing Price (MCP) baseline
    if cleared_trades:
        mcp = round(sum(t["cleared_price"] for t in cleared_trades) / len(cleared_trades), 2)
    else:
        mcp = round((grid_buy_tariff + grid_sell_tariff) / 2.0, 2)

    return {
        "slot_mcp": mcp,
        "total_supply_kw": round(total_supply, 2),
        "total_demand_kw": round(total_demand, 2),
        "p2p_cleared_volume_kw": round(matched_volume, 2),
        "grid_import_kw": round(unmatched_demand, 2),
        "grid_export_kw": round(unmatched_supply, 2),
        "grid_import_cost": round(unmatched_demand * grid_buy_tariff, 2),
        "grid_export_revenue": round(unmatched_supply * grid_sell_tariff, 2),
        "trades": cleared_trades
    }

if __name__ == "__main__":
    # Test Standalone Market Clearing Execution
    test_bids = [
        {"id": "alice", "e_tra_kw": -0.74, "bid_price": 0.86},
        {"id": "bob", "e_tra_kw": 1.20, "bid_price": 0.50},
        {"id": "david", "e_tra_kw": -0.40, "bid_price": 0.90}
    ]
    print("--- Market Engine Test Output ---")
    result = clear_market(test_bids)
    print(json.dumps(result, indent=2))