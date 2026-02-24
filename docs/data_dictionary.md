# Data Dictionary

This document describes the schema and structure of all datasets used in the HVAC occupancy forecasting project.

**Note:** Raw data files are not committed to the repository. Contact Kevin/Nada/Ashwin to obtain access to the shared dataset bundle.

---

## Occupancy Data

**Source:** Wi-Fi/locator system  
**Location:** `data/raw/occupancy/`  
**Format:** CSV (TBD)  
**Time Range:** ~2 years historical data  
**Frequency:** ~15 minutes

### Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `timestamp` | datetime | Timestamp of observation | 2024-01-15 08:30:00 |
| `zone_id` | string | Unique identifier for zone/room | BH-101 |
| `occupancy_count` | int | Number of occupants detected | 12 |

**TODO:**
- [ ] Confirm actual column names from raw data files
- [ ] Document any data quality issues (gaps, anomalies)
- [ ] Add sample data snippet

### Notes
- Occupancy is derived from Wi-Fi connection counts or locator system
- May undercount (not everyone on Wi-Fi) or overcount (multiple devices per person)
- Weekend/holiday patterns differ significantly from weekdays

---

## HVAC Data

**Source:** Building Management System (BMS)  
**Location:** `data/raw/hvac/`  
**Format:** CSV (TBD)  
**Time Range:** 3-4 months synchronized with occupancy  
**Frequency:** ~15 minutes

### 2024 Bren Hall Weekly Export Overview

Use this section as the onboarding reference for the imported folder:
`data/raw/hvac/brenhall_2024_weekly/` (source bundle label: `2024 HVAC Data (Bren Hall)`).

#### Scope

- Building: Bren Hall (2024 weekly BMS exports)
- Files currently imported: 14 CSV files
- Coverage in repository: `2024-04-28` through `2024-08-03` (inclusive)
- Shape per file: 672 rows x 5,956 columns
- Combined shape across imported weeks: 9,408 rows x 5,956 columns (before cleaning/normalization)
- Known raw-data issues:
  - Mixed units embedded in values (examples: `ppm`, `cfm`, `%`)
  - Duplicate column names (379 duplicate headers in each weekly export)
  - Very wide schema, which makes manual inspection and ad hoc notebook work error-prone

#### Cadence

- Sampling interval: 15 minutes
- File cadence: 1 file per week
- Expected rows per full week: 672 (`7 days * 24 hours * 4 samples/hour`)
- Timestamp format example: `2024-04-28T00:00:00-07:00 Los_Angeles`
- Timezone appears embedded in each timestamp string (`-07:00 Los_Angeles`) and should be normalized during ingestion

#### File Naming

- Current observed pattern: `BrenHall2024Week_<Mon><Day>.csv`
- Examples:
  - `BrenHall2024Week_Apr28.csv`
  - `BrenHall2024Week_May5.csv`
  - `BrenHall2024Week_Jul28.csv`
- Interpretation: `<Mon><Day>` corresponds to week start date (Sunday 00:00 local time in the current exports)

#### Contributor Onboarding Notes

- Do not assume column names are unique in raw exports; enforce deterministic renaming before transforms.
- Do not parse measurement columns as numeric until units are stripped and standardized.
- Preserve the raw files as immutable source artifacts; write cleaned outputs to `data/interim/` or `data/processed/`.

### Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `timestamp` | datetime | Timestamp of observation | 2024-01-15 08:30:00 |
| `zone_id` | string | Unique identifier for zone/room | BH-101 |
| `setpoint_heat` | float | Heating setpoint (°F) | 70.0 |
| `setpoint_cool` | float | Cooling setpoint (°F) | 74.0 |
| `actual_temp` | float | Measured zone temperature (°F) | 71.5 |
| `hvac_mode` | string | Current mode (heat/cool/off/auto) | heat |
| `energy_kwh` | float | Energy consumption for period | 2.5 |

**TODO:**
- [ ] Confirm actual column names and units from BMS export
- [ ] Document HVAC zone to occupancy zone mapping
- [ ] Add information about HVAC system type (VAV, FCU, etc.)

### Notes
- Energy may be estimated or metered depending on BMS capabilities
- Some zones may share HVAC equipment (zone grouping)

---

## Weather Data

**Source:** TBD (NOAA, local weather station, or campus weather)  
**Location:** `data/raw/weather/`  
**Format:** CSV  
**Time Range:** Aligned with occupancy/HVAC data  
**Frequency:** Hourly

### Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `timestamp` | datetime | Timestamp of observation | 2024-01-15 08:00:00 |
| `temperature` | float | Outdoor temperature (°F) | 45.2 |
| `humidity` | float | Relative humidity (%) | 65.0 |
| `wind_speed` | float | Wind speed (mph) | 8.5 |
| `cloud_cover` | float | Cloud cover (%) | 75.0 |
| `precip` | float | Precipitation (inches) | 0.0 |

**TODO:**
- [ ] Identify weather data source
- [ ] Confirm timezone alignment with building data
- [ ] Add solar radiation if available (affects cooling load)

---

## Time-of-Use (TOU) Pricing Data

**Source:** Utility rate schedule  
**Location:** `data/raw/tou/`  
**Format:** CSV  
**Update Frequency:** Static (updates seasonally or annually)

### Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `period_type` | string | Rate period name | peak |
| `start_hour` | int | Period start (hour of day, 0-23) | 14 |
| `end_hour` | int | Period end (hour of day, 0-23) | 19 |
| `rate_kwh` | float | Electricity rate ($/kWh) | 0.28 |
| `days` | string | Days this applies (weekday/weekend/all) | weekday |
| `season` | string | Season (summer/winter/all) | summer |

**TODO:**
- [ ] Obtain actual TOU schedule from facilities/utility
- [ ] Document demand charges if applicable
- [ ] Add holiday schedule handling

### Notes
- TOU rates vary by season (summer rates typically higher)
- Peak periods are typically afternoon hours on weekdays
- Demand charges may apply based on peak usage

---

## Space Metadata

**Source:** Facilities database / floor plans  
**Location:** `data/raw/space_metadata/`  
**Format:** CSV  
**Update Frequency:** Static (rarely changes)

### Schema

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `zone_id` | string | Unique identifier for zone/room | BH-101 |
| `room_name` | string | Human-readable room name | Conference Room A |
| `room_type` | string | Room category | classroom |
| `floor` | int | Floor number | 1 |
| `area_sqft` | float | Room area (sq ft) | 450.0 |
| `is_external` | bool | Has external walls/windows | True |
| `hvac_zone_id` | string | HVAC zone (if different) | BH-HVAC-1A |
| `max_occupancy` | int | Design/code maximum occupancy | 30 |

**TODO:**
- [ ] Obtain space table from facilities
- [ ] Map occupancy zones to HVAC zones
- [ ] Add room adjacency information if useful

### Room Types
- `classroom` - Teaching spaces
- `office` - Faculty/staff offices
- `conference` - Meeting rooms
- `lab` - Research/teaching labs
- `common` - Hallways, lobbies, break rooms
- `other` - Storage, mechanical, restrooms

---

## Processed Data

**Location:** `data/processed/`  
**Format:** Parquet or CSV

### Feature-Ready Dataset

Combined dataset with aligned occupancy, HVAC, weather, and engineered features.

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | datetime | Aligned timestamp |
| `zone_id` | string | Zone identifier |
| `occupancy_count` | int | Occupancy |
| `setpoint_heat` | float | Heating setpoint |
| `setpoint_cool` | float | Cooling setpoint |
| `actual_temp` | float | Zone temperature |
| `hvac_on` | bool | Is HVAC actively running |
| `energy_kwh` | float | Energy consumption |
| `outdoor_temp` | float | Weather temperature |
| `tou_rate` | float | Current electricity rate |
| `hour` | int | Hour of day (0-23) |
| `day_of_week` | int | Day of week (0=Mon, 6=Sun) |
| `is_weekend` | bool | Weekend flag |
| `is_opportunity` | bool | Zero occupancy + HVAC on |

**TODO:**
- [ ] Finalize feature list based on modeling needs
- [ ] Document data quality metrics for processed data
