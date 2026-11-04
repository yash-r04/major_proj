import numpy as np

MAX_TRA_KW = 5.0      # Max grid/P2P transfer (kW)
MIN_PRICE = 2.50      # Feed-in tariff floor (₹/kWh)
MAX_PRICE = 6.00      # Grid import tariff ceiling (₹/kWh)
MAX_FLEX_KW = 1.5     # Max flex load (kW)

def scale_actions(raw_action):
    """Rescales PPO continuous outputs from [-1, 1] to real units."""
    a0, a1, a2 = raw_action[0], raw_action[1], raw_action[2]
    e_tra_kw = float(a0 * MAX_TRA_KW)
    bid_price = float(MIN_PRICE + (a1 + 1.0) * 0.5 * (MAX_PRICE - MIN_PRICE))
    flex_kw = float((a2 + 1.0) * 0.5 * MAX_FLEX_KW)
    return e_tra_kw, bid_price, flex_kw

def build_obs_vector(pv, load, soc, slot, profile):
    """Builds 10-element state embedding profile preference weights (omega)."""
    profile_map = {
        "economic": (0.8, 0.1, 0.1),
        "autarky": (0.2, 0.2, 0.6),
        "environmental": (0.3, 0.6, 0.1)
    }
    w_cost, w_batt, w_grid = profile_map.get(profile, (0.5, 0.25, 0.25))

    return np.array([
        float(pv), float(load), float(soc),
        float(MAX_PRICE), float(MIN_PRICE), float(slot),
        float(w_cost), float(w_batt), float(w_grid), 0.0
    ], dtype=np.float32)

def decide(payload, model=None):
    pv = float(payload.get("pv_kw", 0.0))
    load = float(payload.get("load_kw", 0.0))
    soc = float(payload.get("soc", 0.5))
    ts = payload.get("ts", 0)
    slot = payload.get("slot", (ts // 3600) % 24)
    profile = payload.get("profile", "economic")

    if model is not None:
        obs = build_obs_vector(pv, load, soc, slot, profile)
        raw_action, _ = model.predict(obs, deterministic=True)
        e_tra_kw, bid_price, flex_kw = scale_actions(raw_action)
    else:
        e_tra_kw = pv - load
        bid_price = 4.00
        flex_kw = 0.0

    # ESS conservation equation: ess = e_tra - pv + load
    ess_kw = float(e_tra_kw - pv + load)

    return {
        "e_tra_kw": round(e_tra_kw, 3),
        "ess_kw": round(ess_kw, 3),
        "bid_price": round(bid_price, 2),
        "flex_kw": round(flex_kw, 3),
        "penalty": 0.0
    }