import os
import sys
import random
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Enable root imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.inference import decide
from market.clearing import clear_market
from ledger.submit_trade import log_trades_to_blockchain

prosumers = [
    {"id": "alice", "profile": "economic", "soc": 0.60},
    {"id": "bob", "profile": "environmental", "soc": 0.40},
    {"id": "david", "profile": "autarky", "soc": 0.75}
]

def generate_24h_telemetry(p_info, slot):
    # Standard bell-curve solar PV generation peaking at 13:00 (1 PM)
    if 6 <= slot <= 18:
        solar_peak = 4.2 if p_info["id"] == "bob" else (3.5 if p_info["id"] == "alice" else 2.8)
        pv_kw = max(0.0, solar_peak * np.sin((slot - 6) * np.pi / 12) + random.uniform(-0.2, 0.2))
    else:
        pv_kw = 0.0
        
    # Household load demand curve (peaks morning 8:00 and evening 20:00)
    load_base = 1.2 + 0.8 * (np.sin((slot - 8) * np.pi / 12) ** 2)
    load_kw = max(0.4, load_base + random.uniform(-0.15, 0.15))
    
    return {
        "id": p_info["id"],
        "ts": 1714589000 + (slot * 3600),
        "pv_kw": round(float(pv_kw), 2),
        "load_kw": round(float(load_kw), 2),
        "soc": round(p_info["soc"], 2),
        "profile": p_info["profile"],
        "seq": slot + 1,
        "sig": "sim_sig"
    }

def run_24h_benchmark():
    print("===============================================================")
    print("   RUNNING 24-HOUR BENCHMARK SIMULATION & PLOT GENERATION      ")
    print("===============================================================\n")
    
    records = []
    
    for slot in range(24):
        slot_bids = []
        total_pv = 0.0
        total_load = 0.0
        
        # 1. PPO Model Decisions for all prosumers
        for p in prosumers:
            telemetry = generate_24h_telemetry(p, slot)
            total_pv += telemetry["pv_kw"]
            total_load += telemetry["load_kw"]
            
            command = decide(telemetry)
            slot_bids.append(command)
            
            # Simple SoC dynamics update for next slot
            p["soc"] = max(0.10, min(0.90, p["soc"] + (command["ess_kw"] * 0.05)))

        # 2. Clear Market
        m_res = clear_market(slot_bids)
        
        # 3. Log to Blockchain Ledger
        tx_hashes = log_trades_to_blockchain(m_res["trades"])
        
        # 4. Calculate Costs (P2P vs Standard Grid Baseline)
        grid_baseline_cost = total_load * 6.00  # Flat ₹6.00/kWh grid tariff
        p2p_market_cost = (m_res["grid_import_cost"] + 
                          sum(t["total_cost"] for t in m_res["trades"]) - 
                          m_res["grid_export_revenue"])

        records.append({
            "slot": slot,
            "total_pv_kw": round(total_pv, 2),
            "total_load_kw": round(total_load, 2),
            "mcp": m_res["slot_mcp"],
            "p2p_volume_kw": m_res["p2p_cleared_volume_kw"],
            "grid_import_kw": m_res["grid_import_kw"],
            "grid_export_kw": m_res["grid_export_kw"],
            "grid_baseline_cost": round(grid_baseline_cost, 2),
            "p2p_market_cost": round(p2p_market_cost, 2),
            "alice_soc": prosumers[0]["soc"],
            "bob_soc": prosumers[1]["soc"],
            "david_soc": prosumers[2]["soc"]
        })
        
    df = pd.DataFrame(records)
    print("\n--- 24-Hour Simulation Complete ---")
    print(f"Total Grid Baseline Cost : ₹{df['grid_baseline_cost'].sum():.2f}")
    print(f"Total P2P Market Cost    : ₹{df['p2p_market_cost'].sum():.2f}")
    print(f"Total Cost Savings       : {((df['grid_baseline_cost'].sum() - df['p2p_market_cost'].sum()) / df['grid_baseline_cost'].sum()) * 100:.1f}%\n")
    
    # --- GENERATE REPORT PLOTS ---
    plots_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "plots")
    os.makedirs(plots_dir, exist_ok=True)
    
    # Plot 1: Solar/Load vs Market Clearing Price (MCP)
    fig, ax1 = plt.subplots(figsize=(10, 5))
    ax2 = ax1.twinx()
    ax1.plot(df['slot'], df['total_pv_kw'], 'g-', label='Total Generation (PV)', linewidth=2)
    ax1.plot(df['slot'], df['total_load_kw'], 'r--', label='Total Demand (Load)', linewidth=2)
    ax2.plot(df['slot'], df['mcp'], 'b-o', label='Market Clearing Price (MCP)', linewidth=1.5)
    ax1.set_xlabel('Simulated Hour Slot of Day (0-23)')
    ax1.set_ylabel('Power (kW)', color='g')
    ax2.set_ylabel('Price (₹/kWh)', color='b')
    plt.title('Figure 1: 24-Hour Community Generation/Demand vs. Market Clearing Price (MCP)')
    ax1.grid(True, linestyle=':', alpha=0.6)
    plt.savefig(os.path.join(plots_dir, "fig1_mcp_vs_generation.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    # Plot 2: Cost Savings Comparison (P2P Market vs Grid Baseline)
    plt.figure(figsize=(10, 5))
    plt.plot(df['slot'], df['grid_baseline_cost'].cumsum(), 'r--', label='Cumulative Grid-Only Cost (No P2P)', linewidth=2)
    plt.plot(df['slot'], df['p2p_market_cost'].cumsum(), 'g-', label='Cumulative P2P DRL Market Cost', linewidth=2)
    plt.xlabel('Simulated Hour Slot of Day (0-23)')
    plt.ylabel('Cumulative Cost (₹)')
    plt.title('Figure 2: Cumulative Energy Expenditure Comparison')
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.savefig(os.path.join(plots_dir, "fig2_cost_savings.png"), dpi=300, bbox_inches='tight')
    plt.close()

    # Plot 3: Battery State of Charge (SoC) Profiles
    plt.figure(figsize=(10, 5))
    plt.plot(df['slot'], df['alice_soc'] * 100, label='Alice (Economic)')
    plt.plot(df['slot'], df['bob_soc'] * 100, label='Bob (Environmental)')
    plt.plot(df['slot'], df['david_soc'] * 100, label='David (Autarky)')
    plt.axhline(y=90, color='r', linestyle=':', label='Max Capacity Limit (90%)')
    plt.axhline(y=10, color='r', linestyle=':', label='Min Threshold Limit (10%)')
    plt.xlabel('Simulated Hour Slot of Day (0-23)')
    plt.ylabel('Battery State of Charge (%)')
    plt.title('Figure 3: Prosumer Battery State of Charge (SoC) Trajectories')
    plt.legend()
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.savefig(os.path.join(plots_dir, "fig3_battery_soc_profiles.png"), dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"[SUCCESS] All 3 major project figures saved to: {plots_dir}")

if __name__ == "__main__":
    run_24h_benchmark()