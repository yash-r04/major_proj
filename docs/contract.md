# Edge-to-Cloud Interface Contract & Data Protocol

## 1. System Overview & Architecture
This document freezes the communication interface, data formats, topic structures, and timing constants between the **Edge Smart Meters (Person A)** and the **Market Clearing & DRL Intelligence Engine (Person B)** over MQTT.

---

## 2. Timing & Time-Scaling Protocol
To allow real-time demonstration during viva and evaluation, physical time is scaled to simulated energy market slots:

* **1 Market Time Slot ($t$):** 1 Simulated Hour = **10 Real-Time Seconds**
* **Sampling Rate:** Smart meter samples sensors every **1 second** and publishes an averaged telemetry payload every **10 seconds**.
* **Timeout Window:** If the device receives no decision payload within **15 seconds** of publishing, it enters local fallback mode.

---

## 3. MQTT Topic Hierarchy

All topics follow a structured hierarchy scoped to the community ID and specific prosumer device:

| Direction | Topic Pattern | Description |
| :--- | :--- | :--- |
| **Device $\rightarrow$ Cloud** | `community/{community_id}/meter/{device_id}` | Telemetry payload (PV, Load, SoC, Profile) |
| **Cloud $\rightarrow$ Device** | `community/{community_id}/command/{device_id}` | Cleared trade command & battery action |
| **System Status** | `community/{community_id}/status` | System health & offline alerts |

*Example:*
* Telemetry Topic: `community/bengaluru_grid/meter/alice`
* Command Topic: `community/bengaluru_grid/command/alice`

---

## 4. Telemetry Schema (Device $\rightarrow$ Cloud)

Published by the ESP32 (or mock script) every time slot.

### JSON Schema Specification
```json
{
  "$schema": "[http://json-schema.org/draft-07/schema#](http://json-schema.org/draft-07/schema#)",
  "title": "MeterTelemetry",
  "type": "object",
  "properties": {
    "id": { "type": "string", "description": "Unique prosumer identifier" },
    "ts": { "type": "integer", "description": "Unix timestamp in seconds (NTP synced)" },
    "pv_kw": { "type": "number", "minimum": 0.0, "maximum": 5.0, "description": "Solar PV power output in kW" },
    "load_kw": { "type": "number", "minimum": 0.0, "maximum": 4.0, "description": "Demanded household load in kW" },
    "soc": { "type": "number", "minimum": 0.1, "maximum": 0.9, "description": "State of Charge of battery (0.1 to 0.9)" },
    "profile": { "type": "string", "enum": ["economic", "environmental", "autarky"], "description": "Selected preference profile" },
    "seq": { "type": "integer", "minimum": 1, "description": "Monotonically increasing sequence counter" },
    "sig": { "type": "string", "description": "ECDSA signature over payload payload fields for tamper protection" }
  },
  "required": ["id", "ts", "pv_kw", "load_kw", "soc", "profile", "seq", "sig"]
}