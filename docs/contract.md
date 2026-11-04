# ASTRA — Automated Smart Trading & Routing Agent
## ESP32 Hardware & Backend HTTP Adapter Contract

## Protocol Overview
Communicates via HTTP POST requests authenticated using HMAC-SHA256 headers.

## Endpoint
`POST /api/decide`

## Required HTTP Headers
- `Content-Type`: `application/json`
- `X-Device-Id`: Device identifier string
- `X-Signature`: Hex-encoded HMAC-SHA256 digest

## Request Payload
```json
{
  "id": "alice",
  "seq": 104,
  "ts": 1711200000,
  "slot": 12,
  "pv_kw": 2.45,
  "load_kw": 1.10,
  "soc": 0.65,
  "profile": "economic",
  "measured_ma": 4500,
  "delivery_ok": true
}