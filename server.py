"""
ASTRA backend: HTTP front door for the ESP32 smart meters.

  POST /api/decide        device -> decision (HMAC-authenticated)
  GET  /api/live          latest reading + decision per device, latest market result, stats
  GET  /api/history       recent readings/decisions   (?id=alice&limit=100)
  GET  /api/market        latest multi-prosumer market clearing
  GET  /api/ledger/blocks recent on-chain trades (falls back to labelled sample data)
  GET  /api/telemetry/24h synthetic 24 h curve (labelled simulated)
  GET  /                  status

Run from the repo root:  python server.py
"""
import hmac, hashlib, json, os, threading, time
from collections import deque
from flask import Flask, request, jsonify
from flask_cors import CORS

BASE = os.path.dirname(os.path.abspath(__file__))

# ---------------- PPO model (loaded once) ----------------
MODEL, MODEL_ERR = None, None
try:
    from stable_baselines3 import PPO
    MODEL = PPO.load(os.path.join(BASE, "agent", "models", "ppo_universal_agent.zip"))
    print("[ASTRA] PPO model loaded")
except Exception as exc:
    MODEL_ERR = str(exc)
    print(f"[ASTRA] PPO model NOT loaded ({exc}); using rule-based decisions")

from agent.inference import decide as model_decide
from market.clearing import clear_slot

try:
    from ledger.submit_trade import log_trades_to_blockchain, log_penalty, ledger_ready, ledger_error
except Exception as exc:                                   # web3 missing etc.
    log_trades_to_blockchain = log_penalty = None
    ledger_ready = lambda: False
    ledger_error = lambda: f"ledger module unavailable ({exc})"

app = Flask(__name__)
CORS(app)

# ---------------- Config ----------------
# Per-device secrets. alice must match DEVICE_SECRET in the ESP32's secrets.h.
DEVICE_KEYS = {
    "alice": os.environ.get("ALICE_SECRET", os.environ.get("alice", "123456789")),
    "bob":   os.environ.get("BOB_SECRET", "bob-sim-secret"),
    "david": os.environ.get("DAVID_SECRET", "david-sim-secret"),
}
TS_WINDOW_S = 30
MARKET_LEAD = "alice"          # the market clears each time this device reports
MARKET_WINDOW_S = 25           # decisions newer than this take part in the market
DR_SLOTS = range(17, 22)       # demo demand-response window (simulated hours)
SOC_MIN, SOC_MAX = 0.10, 0.90
BATT_KWH, EFF, ESS_MAX_KW = 7.0, 0.90, 2.5
MIN_PRICE, MAX_PRICE = 2.50, 6.00

# ---------------- In-memory store ----------------
LOCK = threading.Lock()
last_seq = {}
HISTORY = deque(maxlen=1000)
LATEST = {}
STATS = {}
LAST_MARKET = {}
LEDGER_LOG = deque(maxlen=200)


def sanitise(pv, load, soc, e_tra_model):
    """Feasible battery action from the intended trade. e_tra = pv + ess - load (ess > 0 = discharge)."""
    ess = e_tra_model - pv + load
    ess = max(-ESS_MAX_KW, min(ESS_MAX_KW, ess))
    if ess > 0:
        ess = min(ess, max((soc - SOC_MIN) * BATT_KWH * EFF, 0.0))
    else:
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


def _async(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


def _ledger_trades(trades, slot):
    try:
        res = log_trades_to_blockchain(trades, slot)
    except Exception as exc:
        print(f"[LEDGER] trade write failed: {exc}")
        return
    for t, r in zip(trades, res):
        LEDGER_LOG.appendleft({
            "block": r["block"], "hash": r["tx_hash"], "gas_used": r["gas_used"],
            "seller": t["seller_id"], "buyer": t["buyer_id"],
            "volume": f"{t['volume_kwh']:.2f} kWh", "price": f"₹{t['price_inr']:.2f}", "slot": slot})
    if res:
        print(f"[LEDGER] {len(res)} trade(s) recorded, last block {res[-1]['block']}")


def _ledger_penalty(dev, slot):
    try:
        r = log_penalty(dev, slot)
        if r:
            LEDGER_LOG.appendleft({"block": r["block"], "hash": r["tx_hash"], "gas_used": r["gas_used"],
                                   "seller": "-", "buyer": "-", "volume": "PENALTY", "price": dev, "slot": slot})
    except Exception as exc:
        print(f"[LEDGER] penalty write failed: {exc}")


def run_market(trigger_slot):
    now = time.time()
    with LOCK:
        recent = [dict(r) for r in LATEST.values() if now - r["server_ts"] <= MARKET_WINDOW_S]
    result = clear_slot(recent)
    result.update(slot=trigger_slot, devices=[r["id"] for r in recent], server_ts=now)
    with LOCK:
        LAST_MARKET.clear()
        LAST_MARKET.update(result)
    if result["trades"] and ledger_ready():
        _async(_ledger_trades, result["trades"], trigger_slot)
    return result


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

    if MODEL is not None:
        out = model_decide({"id": dev, "slot": slot, "pv_kw": pv, "load_kw": load, "soc": soc,
                            "profile": profile}, model=MODEL)
        e_tra_model, bid, flex_model = out["e_tra_kw"], out["bid_price"], out["flex_kw"]
        source = "model"
    else:
        e_tra_model, bid = rule_based(pv, load, soc, profile)
        flex_model, source = 0.0, "rules"

    bid = max(MIN_PRICE, min(MAX_PRICE, bid))
    ess, e_tra = sanitise(pv, load, soc, e_tra_model)
    flex = 0.8 if slot in DR_SLOTS else 0.0          # demo demand-response window
    penalty = d.get("delivery_ok") is False          # previous slot's delivery failed

    rec = {"server_ts": time.time(), "id": dev, "slot": slot, "seq": d["seq"], "profile": profile,
           "pv_kw": pv, "load_kw": load, "soc": soc,
           "e_tra_kw": round(e_tra, 2), "ess_kw": round(ess, 2), "bid_price": round(bid, 2),
           "flex_kw": flex, "penalty": penalty, "source": source,
           "model_e_tra_kw": round(e_tra_model, 2), "model_flex_kw": round(flex_model, 2),
           "measured_ma": d.get("measured_ma"), "load_on": d.get("load_on"),
           "delivery_ok": d.get("delivery_ok"), "fault": d.get("fault")}
    with LOCK:
        HISTORY.append(rec)
        LATEST[dev] = rec
        st = STATS.setdefault(dev, {"requests": 0, "penalties": 0})
        st["requests"] += 1
        st["penalties"] += int(penalty)

    if penalty and log_penalty is not None and ledger_ready():
        _async(_ledger_penalty, dev, slot)
    if dev == MARKET_LEAD:
        run_market(slot)

    print(f"[{source}] {dev} slot={slot} seq={d['seq']} pv={pv} load={load} soc={soc} {profile}: "
          f"model e_tra={e_tra_model:.2f} -> e_tra={e_tra:.2f} ess={ess:.2f} bid={bid:.2f} flex={flex} "
          f"I={d.get('measured_ma')}mA delivery_ok={d.get('delivery_ok')}")

    return jsonify(e_tra_kw=round(e_tra, 2), ess_kw=round(ess, 2), bid_price=round(bid, 2),
                   flex_kw=flex, penalty=penalty)


# ---------------- Read endpoints for the dashboard ----------------
@app.get("/")
def home():
    return jsonify(status="active", service="ASTRA — Automated Smart Trading & Routing Agent",
                   decide_endpoint="/api/decide", model_loaded=MODEL is not None,
                   model_error=MODEL_ERR, ledger_ready=ledger_ready(),
                   ledger_error=None if ledger_ready() else ledger_error())


@app.get("/api/live")
def api_live():
    with LOCK:
        return jsonify(status="success", server_time=time.time(), model_loaded=MODEL is not None,
                       devices=dict(LATEST), stats=dict(STATS), market=dict(LAST_MARKET))


@app.get("/api/history")
def api_history():
    dev = request.args.get("id")
    limit = min(int(request.args.get("limit", 100)), 1000)
    with LOCK:
        rows = [r for r in HISTORY if dev is None or r["id"] == dev]
    return jsonify(status="success", data=rows[-limit:])


@app.get("/api/market")
def api_market():
    with LOCK:
        return jsonify(status="success", market=dict(LAST_MARKET))


@app.get("/api/ledger/blocks")
def api_ledger():
    with LOCK:
        logs = list(LEDGER_LOG)
    if logs:
        return jsonify(status="success", simulated=False, logs=logs)
    return jsonify(status="success", simulated=True, logs=[
        {"block": 14, "hash": "0xbcf8070e9264bcaf12fea729dd7744d339dc7086ec4ffb6642f26f82c50e06e6",
         "seller": "Bob (Node-1)", "buyer": "Alice (Node-2)", "volume": "0.74 kWh", "price": "₹3.50"},
        {"block": 13, "hash": "0x8619e5f8b2b4ad96c4f6b216fe56b64713ef738f225ed51cc667cafa5b73f8fb",
         "seller": "Bob (Node-1)", "buyer": "David (Node-3)", "volume": "0.40 kWh", "price": "₹3.50"}])


@app.get("/api/telemetry/24h")
def get_24h_telemetry():
    """Synthetic curve for the demo chart (NOT measured data)."""
    import numpy as np
    results = []
    for hour in range(24):
        solar = float(np.maximum(0.0, 5.0 * np.sin(np.pi * (hour - 6) / 12))) if 6 <= hour <= 18 else 0.0
        load = float(1.2 + 1.5 * np.exp(-((hour - 8) ** 2) / 4) + 2.0 * np.exp(-((hour - 20) ** 2) / 4))
        mcp = round(max(2.50, min(6.00, 5.25 - (solar * 0.45))), 2)
        results.append({"hour": f"{hour:02d}:00", "solar_pv": round(solar, 2),
                        "load_demand": round(load, 2), "mcp": mcp})
    return jsonify(status="success", simulated=True,
                   summary={"total_p2p_traded": 14.28, "cost_savings_pct": 59.3, "grid_rate": 5.25, "avg_mcp": 3.42},
                   data=results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
