# System Design: HVAC Occupancy Forecasting & Control

## Overview
This document describes the high-level architecture for the occupancy-driven HVAC forecasting and control system for campus buildings (starting with Brent Hall).

The system aims to:
- Forecast future building occupancy using historical data
- Identify opportunities for energy savings when zones are unoccupied
- Recommend HVAC setpoint adjustments to reduce energy consumption while maintaining comfort

**TODO:** Add system context diagram showing the overall scope and boundaries.

## Inputs and Outputs

### Inputs
| Data Source | Description | Update Frequency |
|-------------|-------------|------------------|
| Occupancy Data | Wi-Fi/locator-derived occupancy counts by zone | ~15 min |
| HVAC Data | Setpoints, states, energy consumption by zone | ~15 min |
| Weather Data | Historical and forecast weather conditions | Hourly |
| TOU Pricing | Time-of-use electricity rates | Static/seasonal |
| Space Metadata | Room/zone attributes (area, type, floor) | Static |

**TODO:** Document specific file formats and column schemas.

### Outputs
| Output | Description | Consumer |
|--------|-------------|----------|
| Occupancy Forecast | Predicted occupancy by zone for next N hours | Control module |
| Savings Analysis | Historical "opportunity for savings" metrics | Reports/dashboards |
| Setpoint Recommendations | Suggested HVAC setpoints by zone/time | Building operators |
| Dashboards | Visualizations of occupancy and savings | Stakeholders |

**TODO:** Define forecast horizons and update frequencies for each output.

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              RAW DATA                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Occupancy │  │   HVAC   │  │ Weather  │  │   TOU    │  │  Space   │  │
│  │  Data    │  │   Data   │  │   Data   │  │  Rates   │  │ Metadata │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  │
└───────┼─────────────┼─────────────┼─────────────┼─────────────┼────────┘
        │             │             │             │             │
        ▼             ▼             ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     DATA INGESTION & PREPROCESSING                       │
│  • Clean and validate raw data                                           │
│  • Align timestamps across sources                                       │
│  • Merge occupancy + HVAC + weather                                      │
│  • Engineer features for modeling                                        │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        PROCESSED FEATURES                                │
│  Feature-ready dataset with aligned occupancy, HVAC, weather, TOU       │
└────────────┬───────────────────────────────────────┬────────────────────┘
             │                                       │
             ▼                                       ▼
┌────────────────────────────┐           ┌────────────────────────────────┐
│    FORECASTING MODULE      │           │    HISTORICAL ANALYSIS          │
│  • Prophet baseline        │           │  • "Opportunity for savings"    │
│  • Transformer model       │           │  • Pattern identification       │
│  • Model evaluation        │           │  • Visualization                │
└────────────┬───────────────┘           └────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     CONTROL / OPTIMIZATION MODULE                        │
│  • Compute optimal setpoints from occupancy forecast                     │
│  • Apply comfort constraints                                             │
│  • Estimate energy and cost savings                                      │
│  • Account for pre-conditioning needs                                    │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                              OUTPUTS                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │   Setpoint   │  │   Savings    │  │  Dashboards  │                   │
│  │   Schedule   │  │   Reports    │  │    & Viz     │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
```

**TODO:** Add sequence diagrams for key workflows (e.g., daily forecast generation).

## Components

### Data Ingestion & Preprocessing (`src/data/`)
**Purpose:** Load raw data from various sources, clean, validate, and merge into a unified dataset.

**Key functions:**
- `load.py`: Load occupancy, HVAC, weather, TOU, and space metadata
- `preprocess.py`: Merge datasets, handle missing values, engineer features

**TODO:**
- [ ] Define data validation rules
- [ ] Document handling of missing data
- [ ] Specify feature engineering pipeline

### Forecasting Module (`src/models/`)
**Purpose:** Predict future occupancy to enable proactive HVAC control.

**Models:**
- **Prophet Baseline** (`prophet_baseline.py`): Time-series forecasting with seasonality
- **Transformer Model** (`transformer_baseline.py`): Deep learning approach for complex patterns

**TODO:**
- [ ] Define model evaluation metrics
- [ ] Document training/retraining schedule
- [ ] Specify forecast horizons (1hr, 4hr, 24hr)

### Control / Optimization Module (`src/control/`)
**Purpose:** Translate occupancy forecasts into actionable HVAC setpoint recommendations.

**Key functions:**
- `optimizer.py`: Compute setpoints that minimize energy while maintaining comfort

**Constraints:**
- Comfort: Min/max temperature bounds
- Pre-conditioning: Allow time to reach target temperature before occupancy
- TOU pricing: Prefer setbacks during high-rate periods

**TODO:**
- [ ] Define optimization objective function
- [ ] Document comfort constraint parameters
- [ ] Specify integration with building management system (BMS)

### Dashboards / Visualization (`src/viz/`)
**Purpose:** Provide visual insights into occupancy patterns, savings opportunities, and system performance.

**Key visualizations:**
- Daily/weekly occupancy heatmaps
- "Opportunity for savings" time series
- Example day timelines (occupancy + HVAC + savings)
- Savings summary dashboards

**TODO:**
- [ ] Design dashboard layouts
- [ ] Determine interactive vs. static visualization needs
- [ ] Plan for stakeholder presentation materials

## Future Work

### Phase 1 (Current Quarter)
- [ ] Data exploration and "opportunity for savings" analysis
- [ ] Basic visualizations for presentation
- [ ] This system design document
- [ ] Baseline Prophet forecasting model

### Phase 2 (Next Quarter)
- [ ] Improved forecasting models (transformer, LSTM)
- [ ] Control policy simulation framework
- [ ] Interactive dashboard

### Phase 3 (Future)
- [ ] Real-time integration with BMS
- [ ] Multi-building rollout
- [ ] Automated model retraining pipeline
- [ ] Mobile app for building managers

**TODO:** Add timeline and resource requirements.
