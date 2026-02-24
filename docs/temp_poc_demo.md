# Temperature PoC Demo (Bren Hall)

This demo is a proof-of-concept that connects directly to the project goal:
occupancy-aware HVAC control and savings opportunity detection.

It uses the imported 2024 Bren Hall HVAC temperature data to:

- Infer occupancy state from AHU thermal behavior (return air temp minus supply air temp)
- Detect historical control opportunities when the model predicts unoccupied while HVAC load is non-trivial
- Forecast the next 7 days and recommend setback windows

## Run

```bash
python3 scripts/build_temp_poc_demo.py
```

Output:

- `demo/temp_poc_demo.html` (presentation-ready interactive demo)

Optional:

```bash
python3 scripts/build_temp_poc_demo.py \
  --output demo/temp_poc_demo.html \
  --json-output demo/temp_poc_payload.json \
  --forecast-hours 168 \
  --opportunity-kw 0.5 \
  --setback-reduction 0.30 \
  --occ-prob-threshold 0.35
```

## Demo Talking Points

- The thermal delta signal cleanly separates occupied vs unoccupied periods.
- A simple threshold model can recover occupancy status with high accuracy.
- The resulting recommendation windows are immediately usable for a control pilot conversation.
