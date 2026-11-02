import time
import random
from inference import decide

prosumers = [
    {"id": "alice", "profile": "economic", "soc": 0.60},
    {"id": "bob", "profile": "environmental", "soc": 0.45},
    {"id": "david", "profile": "autarky", "soc": 0.80}
]

def generate_telemetry(p_info, seq):
    return {
        "id": p_info["id"],
        "ts": int(time.time()),
        "pv_kw": round(random.uniform(1.0, 4.5), 2),
        "load_kw": round(random.uniform(0.5, 3.0), 2),
        "soc": round(p_info["soc"], 2),
        "profile": p_info["profile"],
        "seq": seq,
        "sig": "simulated_signature"
    }

def run_simulation(steps=5):
    print("Starting 3-Prosumer Simulation Sandbox...\n")
    for seq in range(1, steps + 1):
        print(f"--- Time Slot Step {seq} ---")
        for p in prosumers:
            telemetry = generate_telemetry(p, seq)
            command = decide(telemetry)
            print(f"[{p['id'].upper()}] Telemetry: PV={telemetry['pv_kw']}kW | Load={telemetry['load_kw']}kW | SoC={telemetry['soc']}")
            print(f"[{p['id'].upper()}] Decision : Traded={command['e_tra_kw']}kW | Price=₹{command['bid_price']} | ESS={command['ess_kw']}kW\n")
        time.sleep(1)

if __name__ == "__main__":
    run_simulation(steps=3)