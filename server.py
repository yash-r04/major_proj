import hmac, hashlib, json, os, sys, time
from flask import Flask, request, jsonify
from flask_cors import CORS

try:
    from agent.inference import decide as model_decide
    MODEL_OK = True
except Exception as exc:
    print(f"[ADAPTER] Model not available ({exc}); using rule-based fallback")
    model_decide = None
    MODEL_OK = False

app = Flask(__name__)
CORS(app)  # Enables cross-origin requests for React dashboard

# Per-device secrets. Must match DEVICE_ID / DEVICE_SECRET in the ESP32's secrets.h.
DEVICE_KEYS = {
    "alice": os.environ.get("alice", "123456789"),
}
TS_WINDOW_S = 30
last_seq = {}

SOC_MIN, SOC_MAX = 0.10, 0.90
BATT_KWH, EFF = 7.0, 0.90
ESS_MAX_KW = 2.5


def sanitise(pv, load, soc, e_tra_model):
    """Derive a feasible battery action from the model's intended trade.
    Energy balance (contract convention): e_tra = pv + ess - load, ess > 0 = discharge."""
    ess = e_tra_model - pv + load
    ess = max(-ESS_MAX_KW, min(ESS_MAX_KW, ess))
    if ess > 0:                                                 # discharge limit
        ess = min(ess, max((soc - SOC_MIN) * BATT_KWH * EFF, 0.0))
    else:                                                       # charge limit
        ess = -min(-ess, max((SOC_MAX - soc) * BATT_KWH / EFF, 0.0))
    return ess, pv + ess - load


def rule_based(pv, load, soc, profile):
    surplus = pv - load
    ess = 0.0
    if surplus > 0.5 and soc < SOC_MAX - 0.02:
        ess = -min(surplus, 2.0)
    elif surplus < -0.5 and soc > SOC_MIN + 0.02:
        ess = min(-surplus, 2.0)
    bid = {"economic": 4.0, "autarky": 4.5, "environmental": 5.0}.get(profile, 4.0)
    return pv + ess - load, bid


@app.get("/")
def home():
    """Root route to verify server status."""
    return jsonify(
        status="active",
        service="ESP32 Hardware Adapter & P2P Trading Engine",
        decide_endpoint="/api/decide",
        model_loaded=MODEL_OK
    )


@app.get("/api/telemetry/24h")
def get_24h_telemetry():
    """Telemetry route for the React dashboard."""
    import numpy as np
    results = []
    
    for hour in range(24):
        solar = float(np.maximum(0.0, 5.0 * np.sin(np.pi * (hour - 6) / 12))) if 6 <= hour <= 18 else 0.0
        load = float(1.2 + 1.5 * np.exp(-((hour - 8)**2) / 4) + 2.0 * np.exp(-((hour - 20)**2) / 4))
        mcp = round(max(2.50, min(6.00, 5.25 - (solar * 0.45))), 2)

        results.append({
            "hour": f"{hour:02d}:00",
            "solar_pv": round(solar, 2),
            "load_demand": round(load, 2),
            "mcp": mcp
        })

    return jsonify(
        status="success",
        summary={
            "total_p2p_traded": 14.28,
            "cost_savings_pct": 59.3,
            "grid_rate": 5.25,
            "avg_mcp": 3.42
        },
        data=results
    )


@app.get("/api/ledger/blocks")
def get_ledger_blocks():
    """Web3 ledger audit feed for the React dashboard."""
    return jsonify(
        status="success",
        logs=[
            {
                "block": 14,
                "hash": "0xbcf8070e9264bcaf12fea729dd7744d339dc7086ec4ffb6642f26f82c50e06e6",
                "seller": "Bob (Node-1)",
                "buyer": "Alice (Node-2)",
                "volume": "0.74 kWh",
                "price": "₹3.50"
            },
            {
                "block": 13,
                "hash": "0x8619e5f8b2b4ad96c4f6b216fe56b64713ef738f225ed51cc667cafa5b73f8fb",
                "seller": "Bob (Node-1)",
                "buyer": "David (Node-3)",
                "volume": "0.40 kWh",
                "price": "₹3.50"
            }
        ]
    )


@app.post("/api/decide")
def api_decide():
    raw = request.get_data()
    dev = request.headers.get("X-Device-Id", "")
    sig = request.headers.get("X-Signature", "")

    key = DEVICE_KEYS.get(dev)
    if key is None:
        return jsonify(error="unknown device"), 403
    good = hmac.new(key.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(good, sig):
        return jsonify(error="bad signature"), 401

    d = json.loads(raw)
    if d.get("id") != dev:
        return jsonify(error="id mismatch"), 403
    if abs(time.time() - d["ts"]) > TS_WINDOW_S:
        return jsonify(error="timestamp out of window"), 400
    if d["seq"] <= last_seq.get(dev, -1):
        return jsonify(error="replay"), 409
    last_seq[dev] = d["seq"]

    pv, load, soc = d["pv_kw"], d["load_kw"], d["soc"]
    slot, profile = d["slot"], d["profile"]

    source = "rules"
    if MODEL_OK:
        out = model_decide({"id": dev, "ts": slot * 3600, "pv_kw": pv, "load_kw": load,
                            "soc": soc, "profile": profile, "seq": d["seq"], "sig": "verified"})
        e_tra_model, bid = out["e_tra_kw"], max(0.0, out["bid_price"])
        source = "model"
    else:
        e_tra_model, bid = rule_based(pv, load, soc, profile)

    ess, e_tra = sanitise(pv, load, soc, e_tra_model)

    flex = 0.8 if 17 <= slot <= 21 else 0.0
    penalty = d.get("delivery_ok") is False

    print(f"[{source}] {dev} slot={slot} seq={d['seq']} pv={pv} load={load} soc={soc} "
          f"{profile}: model e_tra={e_tra_model:.2f} -> e_tra={e_tra:.2f} ess={ess:.2f} "
          f"bid={bid:.2f} flex={flex} I={d.get('measured_ma')}mA delivery_ok={d.get('delivery_ok')}")

    return jsonify(e_tra_kw=round(e_tra, 2), ess_kw=round(ess, 2), bid_price=round(bid, 2),
                   flex_kw=flex, penalty=penalty)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)