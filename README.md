# HVAC Occupancy Forecasting

Occupancy-driven HVAC forecasting and control for campus buildings (starting with Brent Hall).  
Goal: use historical **occupancy**, **HVAC**, **weather**, and **TOU pricing** data to:
- Forecast **future occupancy**
- Propose **setpoint control strategies**
- Estimate **potential energy and cost savings** while maintaining comfort

---

## Project Structure

- `data/`
  - `raw/` – original source data (not committed to Git):
    - `occupancy/` – Wi-Fi/locator-derived occupancy or occupancy tables
    - `hvac/` – HVAC operation / setpoint / energy data
    - `weather/` – historical weather data aligned by timestamp
    - `tou/` – time-of-use pricing data
  - `interim/` – cleaned and merged intermediate datasets
  - `processed/` – feature-ready datasets for modeling and control

- `notebooks/`
  - `01_exploration_opportunity_savings.ipynb` – initial EDA + “opportunity for savings” analysis
  - `02_forecasting_baselines.ipynb` – Prophet / transformer / other baseline models
  - `03_control_simulation.ipynb` – simulate control policies and estimate savings

- `src/`
  - `data/` – data loading and preprocessing utilities
  - `models/` – forecasting models (Prophet, transformer, etc.)
  - `control/` – optimization / control logic for setpoints and savings
  - `viz/` – plotting and dashboard utilities

- `docs/`
  - `data_dictionary.md` – description of each dataset (columns, units, time ranges)
  - `system_design.md` – high-level architecture, components, and diagrams

---

## Getting Started

### 1. Clone the Repository

```bash
git clone <REPO_URL>
cd hvac-occupancy-forecasting
2. Set Up Environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
> Note: requirements.txt will be populated as we standardize libraries (pandas, numpy, matplotlib/plotly, scikit-learn, Prophet, etc.).

3. Data Access
Raw data is not stored in Git. To work with the project:

Obtain access to the shared dataset bundle (from Kevin/Nada/Ashwin).
Place files in the corresponding data/raw/... subfolders.
See docs/data_dictionary.md for filenames, schemas, and time ranges.

4. Initial Milestones (This Quarter)
Opportunity-for-Savings Analysis
Define “opportunity for savings” (e.g., unoccupied zones with active HVAC).
Compute and visualize potential savings over time using historical data.
Produce plots for the end-of-quarter presentation.
High-Level System Design

Document inputs/outputs for the controller black box.
Draft data flow and component diagrams (docs/system_design.md).
Baseline Forecasting Model



