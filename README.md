# HVAC Occupancy Forecasting

Occupancy-driven HVAC forecasting and control for campus buildings (starting with Brent Hall).

## Goals

Use historical **occupancy**, **HVAC**, **weather**, and **TOU pricing** data to:
- Forecast **future occupancy** using time-series models
- Identify **opportunities for energy savings** when zones are unoccupied
- Propose **setpoint control strategies** to reduce energy consumption
- Estimate **potential energy and cost savings** while maintaining comfort

---

## Project Structure

```
hvac-occupancy-forecasting/
├── README.md
├── .gitignore
├── requirements.txt
│
├── data/
│   ├── raw/                    # Original source data (not committed to Git)
│   │   ├── occupancy/          # Wi-Fi/locator-derived occupancy data
│   │   ├── hvac/               # HVAC operation, setpoints, energy data
│   │   ├── weather/            # Historical weather data
│   │   ├── tou/                # Time-of-use pricing data
│   │   └── space_metadata/     # Space tables, room metadata
│   ├── interim/                # Cleaned and merged intermediate datasets
│   └── processed/              # Feature-ready datasets for modeling
│
├── notebooks/
│   ├── 01_exploration_opportunity_savings.ipynb  # EDA + savings analysis
│   ├── 02_forecasting_baselines.ipynb            # Prophet/transformer models
│   └── 03_control_simulation.ipynb               # Control policy simulations
│
├── src/
│   ├── __init__.py
│   ├── data/                   # Data loading and preprocessing
│   │   ├── __init__.py
│   │   ├── load.py             # Functions to load raw data
│   │   └── preprocess.py       # Cleaning, merging, feature engineering
│   ├── models/                 # Forecasting models
│   │   ├── __init__.py
│   │   ├── prophet_baseline.py # Prophet occupancy forecast
│   │   └── transformer_baseline.py  # Transformer-based forecasting
│   ├── control/                # Optimization and control logic
│   │   ├── __init__.py
│   │   └── optimizer.py        # Setpoint optimization, savings estimation
│   └── viz/                    # Visualization utilities
│       ├── __init__.py
│       └── dashboards.py       # Plotting and dashboard functions
│
└── docs/
    ├── system_design.md        # High-level architecture and data flow
    └── data_dictionary.md      # Dataset schemas and descriptions
```

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/DataWhisk/hvac-occupancy-forecasting.git
cd hvac-occupancy-forecasting
```

### 2. Set Up Environment

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Data Access

**Raw data is not stored in Git.** To work with the project:

1. Obtain access to the shared dataset bundle (from Kevin/Nada/Ashwin)
2. Place files in the corresponding `data/raw/...` subfolders:
   - `data/raw/occupancy/` - Occupancy CSV files
   - `data/raw/hvac/` - HVAC data exports
   - `data/raw/weather/` - Weather data
   - `data/raw/tou/` - TOU pricing schedules
   - `data/raw/space_metadata/` - Room/zone metadata

See [`docs/data_dictionary.md`](docs/data_dictionary.md) for filenames, schemas, and time ranges.

### 4. Run Notebooks

Start with the exploration notebook:

```bash
jupyter notebook notebooks/01_exploration_opportunity_savings.ipynb
```

---

## Initial Milestones (This Quarter)

### 1. Opportunity-for-Savings Analysis
- [ ] Define "opportunity for savings" (e.g., unoccupied zones with active HVAC)
- [ ] Compute and visualize potential savings over time using historical data
- [ ] Produce plots for the end-of-quarter presentation

### 2. High-Level System Design
- [ ] Document inputs/outputs for the controller black box
- [ ] Draft data flow and component diagrams ([`docs/system_design.md`](docs/system_design.md))

### 3. Baseline Forecasting Model
- [ ] Implement Prophet baseline for occupancy forecasting
- [ ] Evaluate model performance on historical data

---

## Key Concepts

### "Opportunity for Savings"
Periods where:
- Occupancy is **zero** (or below threshold)
- HVAC is **actively running** (consuming energy)

These represent the maximum potential savings from occupancy-aware control.

### Control Strategy
1. **Forecast** future occupancy using time-series models
2. **Identify** upcoming low/zero occupancy periods
3. **Adjust** HVAC setpoints (setback temperatures) during these periods
4. **Pre-condition** zones before expected occupancy returns
5. **Estimate** energy and cost savings using TOU pricing

---

## Data Overview

| Dataset | Description | Time Range |
|---------|-------------|------------|
| Occupancy | Wi-Fi/locator-derived counts by zone | ~2 years |
| HVAC | Setpoints, states, energy by zone | 3-4 months |
| Weather | Temperature, humidity, etc. | Aligned with HVAC |
| TOU | Time-of-use electricity rates | Static/seasonal |
| Space Metadata | Room attributes (type, area, floor) | Static |

---

## Contributing

1. Create a feature branch from `main`
2. Make your changes with clear commit messages
3. Ensure notebooks run without errors
4. Submit a pull request for review

---

## License

This project is for academic/research purposes. Contact the project advisors for usage permissions.
