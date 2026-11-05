import time
import random
import sys
import os
import numpy as np

# Add root folder to path to enable clean imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.inference import decide
from market.clearing import clear_slot

prosumers = [
    {"id": "alice", "profile": "economic", "soc": 0.60},
    {"id": "bob", "profile": "environmental", "soc": 0.45},
    {"id": "david", "profile": "autarky", "soc": 0.80}
]

def generate_telemetry(p_info, seq, slot):
    # Simulated PV curve (peaks mid-day) and Load curve
    pv_base = max(0.0, 4.0 * round(abs(np.sin(slot * np.pi / 12)), 2)) if 6 <= slot <= 18 else 0.0
    return {
        "id": p_info["id"],
        "ts": 1714589000 + (slot * 3600),
        "pv_kw": round(pv_base + random.uniform(0.1, 0.5), 2),
        "load_kw": round(random.uniform(0.8, 2.5), 2),
        "soc": round(p_info["soc"], 2),
        "profile": p_info["profile"],
        "seq": seq,
        "sig": "simulated_signature"
    }

def run_market_simulation(slots=3):
    import numpy as np
    print("=============================================================")
    print("  STARTING END-TO-END DRL P2P MARKET SIMULATION (DAY 2)  ")
    print("=============================================================\n")
    
    for slot in range(slots):
        print(f"==================== TIME SLOT {slot}:00 ====================")
        slot_bids = []
        
        # 1. Collect PPO Model Decisions for all prosumers
        for p in prosumers:
            telemetry = generate_telemetry(p, slot + 1, slot)
            command = decide(telemetry)
            command['id'] = p['id']
            slot_bids.append(command)
            print(f"[{p['id'].upper()}] PV={telemetry['pv_kw']}kW | Load={telemetry['load_kw']}kW | Bid Vol={command['e_tra_kw']}kW | Price=₹{command['bid_price']}")

        # 2. Clear the market (midpoint double auction, leftovers go to the grid)
        r = clear_slot(slot_bids)

        print("\n--- MARKET CLEARING SUMMARY ---")
        print(f"Market Clearing Price (MCP) : {'Rs %s/kWh' % r['mcp'] if r['mcp'] is not None else 'no P2P trades'}")
        print(f"Total P2P Traded Volume     : {r['p2p_kwh']} kWh")
        print(f"Grid Import Deficit         : {r['grid_import_kwh']} kWh (Cost: Rs {r['grid_import_cost']})")
        print(f"Grid Export Surplus         : {r['grid_export_kwh']} kWh (Rev: Rs {r['grid_export_revenue']})")
        for t in r["trades"]:
            print(f"  * {t['seller_id'].upper()} ---> {t['buyer_id'].upper()} : {t['volume_kwh']} kWh @ Rs {t['price_inr']}/kWh")
        if not r["trades"]:
            print("No direct P2P matches cleared this slot; fallback to grid.")
        print("\n")

if __name__ == "__main__":
    run_market_simulation(slots=3)