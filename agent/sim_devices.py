"""
Simulated prosumers (Bob and David) that talk to the server exactly like the ESP32 does.
Gives the market several participants while the real ESP32 plays Alice.

Run (server already running):   python agent/sim_devices.py [http://127.0.0.1:5000]
"""
import hashlib, hmac, json, math, os, random, sys, time
import requests

URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5000").rstrip("/") + "/api/decide"
SLOT_S = 10
SIMS = [
    {"id": "bob",   "profile": "environmental", "secret": os.environ.get("BOB_SECRET", "bob-sim-secret"),     "soc": 0.45, "pv_scale": 4.0},
    {"id": "david", "profile": "autarky",       "secret": os.environ.get("DAVID_SECRET", "david-sim-secret"), "soc": 0.80, "pv_scale": 2.5},
]
OMEGA = {"economic": [0.3, 0.6, 0.1, 0.0], "autarky": [0.3, 0.1, 0.5, 0.1], "environmental": [0.3, 0.1, 0.1, 0.5]}
BATT_KWH, EFF = 7.0, 0.90
seq = int(time.time())


def telemetry(s, slot):
    pv = s["pv_scale"] * max(0.0, math.sin(math.pi * (slot - 6) / 12)) if 6 <= slot <= 18 else 0.0
    load = 1.2 + 1.3 * math.exp(-((slot - 8) ** 2) / 4) + 1.8 * math.exp(-((slot - 20) ** 2) / 4)
    return round(pv * random.uniform(0.9, 1.1), 2), round(load * random.uniform(0.9, 1.1), 2)


def apply_ess(s, ess):
    if ess > 0:
        s["soc"] -= ess / EFF / BATT_KWH
    else:
        s["soc"] += -ess * EFF / BATT_KWH
    s["soc"] = min(0.9, max(0.1, s["soc"]))


slot = 12
print(f"Simulating {[s['id'] for s in SIMS]} -> {URL} (Ctrl+C to stop)")
while True:
    for s in SIMS:
        seq += 1
        pv, load = telemetry(s, slot % 24)
        body = json.dumps({"id": s["id"], "ts": int(time.time()), "slot": slot % 24, "seq": seq,
                           "pv_kw": pv, "load_kw": load, "soc": round(s["soc"], 2), "profile": s["profile"],
                           "omega": OMEGA[s["profile"]], "delivery_ok": True, "fault": False}).encode()
        sig = hmac.new(s["secret"].encode(), body, hashlib.sha256).hexdigest()
        try:
            r = requests.post(URL, data=body, timeout=5, headers={
                "Content-Type": "application/json", "X-Device-Id": s["id"], "X-Signature": sig})
            if r.ok:
                j = r.json(); apply_ess(s, j["ess_kw"])
                print(f"{s['id']:5s} slot={slot % 24:2d} pv={pv} load={load} -> e_tra={j['e_tra_kw']} bid={j['bid_price']}")
            else:
                print(s["id"], "HTTP", r.status_code, r.text.strip())
        except requests.RequestException as exc:
            print(s["id"], "request failed:", exc)
    slot += 1
    time.sleep(SLOT_S)
