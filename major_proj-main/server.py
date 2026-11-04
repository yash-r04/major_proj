"""
HTTP adapter between the ESP32 and the major_proj backend.

Put this file in the ROOT of the major_proj repo (next to agent/, market/, ledger/):
    pip install flask
    python server.py

It does three jobs:
  1. Authenticates the device (HMAC-SHA256 over the raw body, timestamp window, seq replay check)
  2. Calls agent.inference.decide() with the payload mapped to what decide() expects
  3. Sanity-checks the result so the ESP32 never receives a physically impossible command

If the model cannot be loaded, it falls back to simple rules and says so in the log.
"""
import hmac, hashlib, json, os, sys, time
from flask import Flask, request, jsonify

try:
    from agent.inference import decide as model_decide
    MODEL_OK = True
except Exception as exc:                      # torch / stable_baselines3 missing, etc.
    print(f"[ADAPTER] Model not available ({exc}); using rule-based fallback")
    model_decide = None
    MODEL_OK = False

app = Flask(__name__)

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
    if ess > 0:                                               # discharge limit
        ess = min(ess, max((soc - SOC_MIN) * BATT_KWH * EFF, 0.0))
    else:                                                     # charge limit
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
        # decide() derives its slot from ts // 3600, so pass the SIMULATED hour as the timestamp.
        out = model_decide({"id": dev, "ts": slot * 3600, "pv_kw": pv, "load_kw": load,
                            "soc": soc, "profile": profile, "seq": d["seq"], "sig": "verified"})
        e_tra_model, bid = out["e_tra_kw"], max(0.0, out["bid_price"])
        source = "model"
    else:
        e_tra_model, bid = rule_based(pv, load, soc, profile)

    ess, e_tra = sanitise(pv, load, soc, e_tra_model)

    flex = 0.8 if 17 <= slot <= 21 else 0.0                    # demand-response window (demo)
    penalty = d.get("delivery_ok") is False                    # previous slot's delivery failed

    print(f"[{source}] {dev} slot={slot} seq={d['seq']} pv={pv} load={load} soc={soc} "
          f"{profile}: model e_tra={e_tra_model:.2f} -> e_tra={e_tra:.2f} ess={ess:.2f} "
          f"bid={bid:.2f} flex={flex} I={d.get('measured_ma')}mA delivery_ok={d.get('delivery_ok')}")

    return jsonify(e_tra_kw=round(e_tra, 2), ess_kw=round(ess, 2), bid_price=round(bid, 2),
                   flex_kw=flex, penalty=penalty)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)