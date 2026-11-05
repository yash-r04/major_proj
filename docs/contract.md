# ASTRA: ESP32 <-> Backend HTTP Contract

## Transport and authentication
`POST /api/decide` with JSON. Every request carries:

| Header | Value |
|---|---|
| `Content-Type` | `application/json` |
| `X-Device-Id` | device id, e.g. `alice` |
| `X-Signature` | lowercase hex HMAC-SHA256 of the **raw request body**, keyed with the device secret |

The server rejects: unknown device (403), bad signature (401), `id` not equal to the header (403),
timestamp more than 30 s from server time (400), and `seq` not greater than the last accepted one (409).

## Request body
```json
{
  "id": "alice",
  "ts": 1730000000,
  "slot": 12,
  "seq": 104,
  "pv_kw": 2.45,
  "load_kw": 1.10,
  "soc": 0.65,
  "profile": "economic",
  "omega": [0.3, 0.6, 0.1, 0.0],
  "last_ess_kw": -1.0,
  "last_commit_kw": 0.8,
  "measured_ma": 8.1,
  "load_on": true,
  "delivery_ok": true,
  "fault": false
}
```
`slot` is the simulated hour (0-23; one slot = 10 s of real time in the demo).
`measured_ma`, `load_on`, `delivery_ok` and `fault` describe the **previous** slot (settlement evidence).
`measured_ma` is omitted when the INA219 is not fitted. `profile` is one of `economic`, `autarky`, `environmental`.

## Response body (200)
```json
{ "e_tra_kw": 1.2, "ess_kw": -0.5, "bid_price": 4.25, "flex_kw": 0.0, "penalty": false }
```

## Sign conventions
- `e_tra_kw > 0` sell to the market, `< 0` buy.
- `ess_kw > 0` battery discharges, `< 0` charges.
- Energy balance: `e_tra_kw = pv_kw + ess_kw - load_kw`.
- `bid_price` in Rs/kWh, limited to 2.50-6.00 (feed-in tariff to grid tariff).
- `flex_kw > 0` asks the device to shed its switchable load (demand response).
- `penalty: true` means the previous slot's delivery check failed.

## Read endpoints (dashboard)
| Endpoint | Returns |
|---|---|
| `GET /api/live` | latest reading and decision per device, latest market result, per-device stats |
| `GET /api/history?id=alice&limit=100` | recent readings and decisions |
| `GET /api/market` | latest multi-prosumer clearing: trades, MCP, grid import/export |
| `GET /api/ledger/blocks` | recent on-chain trades and penalties (`simulated: true` when showing sample data) |
| `GET /api/telemetry/24h` | synthetic 24 h curve, not measured data (`simulated: true`) |
