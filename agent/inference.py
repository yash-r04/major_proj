import os
import numpy as np
from stable_baselines3 import PPO

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "ppo_universal_agent.zip")

print("Loading PPO model...")
try:
    model = PPO.load(MODEL_PATH)
    print("Model loaded successfully!")
except Exception as e:
    print(f"Error loading model: {e}")
    model = None

def decide(meter_payload: dict) -> dict:
    prosumer_id = meter_payload.get("id")
    ts = meter_payload.get("ts", 0)
    pv_kw = float(meter_payload.get("pv_kw", 0.0))
    load_kw = float(meter_payload.get("load_kw", 0.0))
    soc = float(meter_payload.get("soc", 0.5))
    profile = meter_payload.get("profile", "economic")
    
    # Calculate current hour slot (0 to 23)
    slot = (ts // 3600) % 24
    
    # --- Construct the 10-element state vector expected by your mini_proj model ---
    # [pv, load, soc, slot/24, net_power, profile_code, 0, 0, 0, 0]
    profile_code = 1.0 if profile == "economic" else (2.0 if profile == "environmental" else 3.0)
    net_power = pv_kw - load_kw
    
    # 10-element observation matching Box(10,)
    obs = np.array([
        pv_kw, 
        load_kw, 
        soc, 
        slot / 24.0, 
        net_power, 
        profile_code, 
        0.0, 0.0, 0.0, 0.0
    ], dtype=np.float32)
    
    # --- Model Inference ---
    if model is not None:
        action, _states = model.predict(obs, deterministic=True)
        
        # Ensure action is parsed cleanly regardless of 1D or 2D array output
        action = np.atleast_1d(action)
        e_tra_kw = round(float(action[0]), 2)
        bid_price = round(float(action[1]), 2) if len(action) > 1 else 4.00
    else:
        e_tra_kw = round(net_power * 0.85, 2)
        bid_price = 4.25 if profile == "economic" else 3.80

    ess_kw = round(-e_tra_kw, 2)

    return {
        "id": prosumer_id,
        "ts": ts + 10,
        "slot": slot,
        "e_tra_kw": e_tra_kw,
        "bid_price": bid_price,
        "ess_kw": ess_kw,
        "shift_flag": 0,
        "ref_trade_id": f"trd_{prosumer_id}_{ts}"
    }

if __name__ == "__main__":
    sample_payload = {
        "id": "alice",
        "ts": 1714589000,
        "pv_kw": 3.45,
        "load_kw": 1.20,
        "soc": 0.65,
        "profile": "economic",
        "seq": 104,
        "sig": "sig_test"
    }
    print("Testing Decision:")
    print(decide(sample_payload))