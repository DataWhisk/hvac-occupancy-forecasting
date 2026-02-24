#!/usr/bin/env python3
"""
Build a demo-ready HTML proof-of-concept using Bren Hall temperature data.

The demo shows:
- A temperature-driven occupancy classifier (using AHU return-supply delta)
- Historical control opportunities (predicted unoccupied + non-trivial HVAC kW)
- A short-horizon forecast with recommended setback windows

Usage:
  python3 scripts/build_temp_poc_demo.py
  python3 scripts/build_temp_poc_demo.py --output demo/temp_poc_demo.html
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


ACTIVE_OCC_STATUS = "AAAB"
NUMERIC_PATTERN = re.compile(r"([-+]?\d*\.?\d+)")


def normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name).strip().lower())


def parse_numeric(series: pd.Series) -> pd.Series:
    extracted = series.astype(str).str.extract(NUMERIC_PATTERN)[0]
    return pd.to_numeric(extracted, errors="coerce")


def downsample_frame(frame: pd.DataFrame, max_points: int) -> pd.DataFrame:
    if len(frame) <= max_points:
        return frame
    indices = np.linspace(0, len(frame) - 1, max_points).round().astype(int)
    return frame.iloc[indices].reset_index(drop=True)


def find_first_column(
    columns: Iterable[str],
    include_tokens: Iterable[str],
    exclude_tokens: Iterable[str] | None = None,
) -> str | None:
    include = [normalize_name(token) for token in include_tokens]
    exclude = [normalize_name(token) for token in (exclude_tokens or [])]
    for col in columns:
        normalized = normalize_name(col)
        if all(token in normalized for token in include) and not any(
            token in normalized for token in exclude
        ):
            return col
    return None


def discover_columns(columns: List[str]) -> Dict[str, str]:
    required = {}
    required["timestamp"] = find_first_column(columns, ["timestamp"])
    required["occ_ahu1"] = find_first_column(columns, ["ah-01", "occ eff status"])
    required["occ_ahu2"] = find_first_column(columns, ["ah-02", "occ eff status"])
    required["return_temp_ahu1"] = find_first_column(columns, ["ah-01", "return air temp"])
    required["supply_temp_ahu1"] = find_first_column(
        columns,
        ["ah-01", "supply air temp"],
        exclude_tokens=["eff sp", "loop", "max sp", "min sp"],
    )
    required["return_temp_ahu2"] = find_first_column(columns, ["ah-02", "return air temp"])
    required["supply_temp_ahu2"] = find_first_column(
        columns,
        ["ah-02", "supply air temp"],
        exclude_tokens=["eff sp", "loop", "max sp", "min sp"],
    )

    hvac_power_col = find_first_column(
        columns,
        ["hvac meter", "hvac elec power"],
        exclude_tokens=[".1"],
    )
    if hvac_power_col is None:
        hvac_power_col = find_first_column(
            columns,
            ["whole building electric meter", "total elec power"],
        )
    required["hvac_power_kw"] = hvac_power_col

    missing = [name for name, col in required.items() if col is None]
    if missing:
        raise ValueError(
            "Missing required columns in combined HVAC file: " + ", ".join(missing)
        )
    return required


def compute_classification_metrics(
    y_true: pd.Series,
    y_pred: pd.Series,
) -> Dict[str, float]:
    y_true_i = y_true.astype(int)
    y_pred_i = y_pred.astype(int)
    tp = int(((y_true_i == 1) & (y_pred_i == 1)).sum())
    tn = int(((y_true_i == 0) & (y_pred_i == 0)).sum())
    fp = int(((y_true_i == 0) & (y_pred_i == 1)).sum())
    fn = int(((y_true_i == 1) & (y_pred_i == 0)).sum())

    total = max(len(y_true_i), 1)
    accuracy = (tp + tn) / total
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)
    balanced_accuracy = (recall + specificity) / 2
    f1 = (2 * precision * recall) / max(precision + recall, 1e-12)

    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "specificity": specificity,
        "balanced_accuracy": balanced_accuracy,
        "f1": f1,
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
    }


def select_threshold(
    train_df: pd.DataFrame,
    delta_col: str,
    target_col: str,
) -> float:
    q01 = float(train_df[delta_col].quantile(0.01))
    q99 = float(train_df[delta_col].quantile(0.99))
    thresholds = np.linspace(q01, q99, 300)

    best_threshold = thresholds[0]
    best_score = -1.0
    for threshold in thresholds:
        prediction = train_df[delta_col] >= threshold
        score = compute_classification_metrics(
            train_df[target_col],
            prediction,
        )["balanced_accuracy"]
        if score > best_score:
            best_score = score
            best_threshold = float(threshold)
    return best_threshold


def infer_step_hours(timestamps: pd.Series) -> float:
    diffs = timestamps.sort_values().diff().dt.total_seconds().dropna()
    if diffs.empty:
        return 0.25
    median_seconds = float(diffs.median())
    if not math.isfinite(median_seconds) or median_seconds <= 0:
        return 0.25
    return median_seconds / 3600.0


def build_recommendation_windows(
    forecast_df: pd.DataFrame,
    step_hours: float,
) -> List[Dict[str, float]]:
    windows: List[Dict[str, float]] = []
    active_rows: List[pd.Series] = []

    for row in forecast_df.itertuples(index=False):
        if bool(row.setback_recommended):
            active_rows.append(row)
            continue

        if active_rows:
            windows.append(summarize_window(active_rows, step_hours))
            active_rows = []

    if active_rows:
        windows.append(summarize_window(active_rows, step_hours))

    windows.sort(key=lambda item: item["projected_savings_kwh"], reverse=True)
    return windows[:10]


def summarize_window(rows: List[pd.Series], step_hours: float) -> Dict[str, float]:
    start = rows[0].timestamp
    end = rows[-1].timestamp + pd.to_timedelta(step_hours, unit="h")
    projected_savings_kwh = float(sum(float(row.projected_savings_kwh) for row in rows))
    mean_hvac_kw = float(np.nanmean([float(row.expected_hvac_kw) for row in rows]))
    mean_occ_prob = float(np.nanmean([float(row.occ_prob_from_temp) for row in rows]))
    duration_hours = len(rows) * step_hours

    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "duration_hours": duration_hours,
        "projected_savings_kwh": projected_savings_kwh,
        "mean_hvac_kw": mean_hvac_kw,
        "mean_occ_prob": mean_occ_prob,
    }


def build_html(payload: Dict[str, object], title: str) -> str:
    payload_json = json.dumps(payload)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    :root {{
      --ink: #0f172a;
      --muted: #475569;
      --paper: #f8fafc;
      --panel: #ffffff;
      --accent: #0b7285;
      --accent-soft: #89d3dc;
      --warm: #c2410c;
      --line: #dbe4ee;
      --ok: #2b8a3e;
      --warn: #b02a37;
      --shadow: 0 18px 38px rgba(15, 23, 42, 0.08);
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: "Space Grotesk", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at 8% 15%, rgba(137, 211, 220, 0.25), transparent 45%),
        radial-gradient(circle at 90% 5%, rgba(194, 65, 12, 0.12), transparent 30%),
        linear-gradient(180deg, #f7fbff 0%, #eef3f8 100%);
      min-height: 100vh;
      padding: 1.2rem;
    }}

    .shell {{
      max-width: 1280px;
      margin: 0 auto;
      display: grid;
      gap: 1rem;
      animation: rise-in 480ms ease-out;
    }}

    @keyframes rise-in {{
      from {{
        opacity: 0;
        transform: translateY(10px);
      }}
      to {{
        opacity: 1;
        transform: translateY(0);
      }}
    }}

    .hero {{
      background: linear-gradient(135deg, #083344 0%, #0f766e 55%, #115e59 100%);
      color: #ecfeff;
      border-radius: 16px;
      padding: 1.2rem 1.3rem;
      box-shadow: var(--shadow);
    }}

    .hero h1 {{
      margin: 0 0 0.35rem 0;
      font-size: 1.45rem;
      letter-spacing: 0.01em;
    }}

    .hero p {{
      margin: 0;
      color: #cffafe;
      max-width: 900px;
      font-size: 0.96rem;
      line-height: 1.45;
    }}

    .chip-row {{
      margin-top: 0.75rem;
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
    }}

    .chip {{
      display: inline-block;
      padding: 0.3rem 0.52rem;
      border-radius: 999px;
      border: 1px solid rgba(236, 254, 255, 0.32);
      color: #e6fffb;
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.72rem;
      letter-spacing: 0.01em;
    }}

    .grid-kpi {{
      display: grid;
      gap: 0.75rem;
      grid-template-columns: repeat(6, minmax(0, 1fr));
    }}

    .kpi {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      box-shadow: var(--shadow);
      padding: 0.8rem 0.85rem;
      min-height: 88px;
    }}

    .kpi label {{
      display: block;
      color: var(--muted);
      font-size: 0.74rem;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      margin-bottom: 0.42rem;
    }}

    .kpi .value {{
      font-size: 1.28rem;
      font-weight: 700;
      line-height: 1.05;
      color: var(--ink);
    }}

    .kpi .sub {{
      margin-top: 0.25rem;
      color: var(--muted);
      font-size: 0.74rem;
      font-family: "IBM Plex Mono", monospace;
    }}

    .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      box-shadow: var(--shadow);
      padding: 0.85rem 0.95rem;
      overflow: hidden;
    }}

    .panel h2 {{
      margin: 0 0 0.4rem 0;
      font-size: 1rem;
    }}

    .panel .explain {{
      margin: 0 0 0.7rem 0;
      color: var(--muted);
      font-size: 0.86rem;
      line-height: 1.45;
    }}

    .two-col {{
      display: grid;
      grid-template-columns: 1.3fr 1fr;
      gap: 0.8rem;
    }}

    .table-wrap {{
      overflow-x: auto;
    }}

    table {{
      border-collapse: collapse;
      width: 100%;
      font-size: 0.85rem;
    }}

    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 0.5rem 0.35rem;
      text-align: left;
      white-space: nowrap;
    }}

    th {{
      color: var(--muted);
      font-weight: 600;
      font-size: 0.74rem;
      letter-spacing: 0.03em;
      text-transform: uppercase;
    }}

    .mono {{
      font-family: "IBM Plex Mono", monospace;
      font-size: 0.76rem;
      color: var(--muted);
      overflow-wrap: anywhere;
      word-break: break-word;
    }}

    .notes {{
      margin: 0;
      padding-left: 1rem;
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.5;
    }}

    .chart-box {{
      position: relative;
      width: 100%;
      overflow: hidden;
    }}

    .chart-box.timeline {{
      height: 320px;
      max-height: 60vh;
    }}

    .chart-box.hourly,
    .chart-box.forecast {{
      height: 300px;
      max-height: 55vh;
    }}

    canvas {{
      display: block;
      width: 100% !important;
      height: 100% !important;
    }}

    @media (max-width: 1120px) {{
      .grid-kpi {{
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }}
      .two-col {{
        grid-template-columns: 1fr;
      }}
    }}

    @media (max-width: 760px) {{
      body {{
        padding: 0.7rem;
      }}
      .grid-kpi {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }}
      .hero h1 {{
        font-size: 1.2rem;
      }}
      .chart-box.timeline,
      .chart-box.hourly,
      .chart-box.forecast {{
        height: 240px;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <h1>{title}</h1>
      <p>
        Temperature-driven occupancy proxy + control opportunity demo on the imported
        Bren Hall 2024 HVAC weekly export. This is a presentation-ready proof-of-concept
        that connects directly to occupancy-aware HVAC setback decisions.
      </p>
      <div class="chip-row">
        <span class="chip" id="chipRange"></span>
        <span class="chip" id="chipRows"></span>
        <span class="chip" id="chipStep"></span>
        <span class="chip" id="chipThreshold"></span>
      </div>
    </section>

    <section class="grid-kpi">
      <div class="kpi">
        <label>Test Accuracy</label>
        <div class="value" id="kpiAccuracy"></div>
        <div class="sub" id="kpiBalanced"></div>
      </div>
      <div class="kpi">
        <label>Historical Opportunity</label>
        <div class="value" id="kpiOppHours"></div>
        <div class="sub">hours with predicted unoccupied + HVAC load</div>
      </div>
      <div class="kpi">
        <label>Historical Avoidable Energy</label>
        <div class="value" id="kpiHistKwh"></div>
        <div class="sub">kWh at configured setback reduction</div>
      </div>
      <div class="kpi">
        <label>Forecast Horizon</label>
        <div class="value" id="kpiForecastHours"></div>
        <div class="sub">hours simulated from learned profile</div>
      </div>
      <div class="kpi">
        <label>Projected Savings</label>
        <div class="value" id="kpiForecastKwh"></div>
        <div class="sub">kWh from recommended windows</div>
      </div>
      <div class="kpi">
        <label>Signal Separation</label>
        <div class="value" id="kpiDeltaGap"></div>
        <div class="sub">occupied vs unoccupied temp delta (F)</div>
      </div>
    </section>

    <section class="panel">
      <h2>Recent Thermal Timeline</h2>
      <p class="explain">
        Cooling delta is AHU return air temp minus supply air temp. The occupancy proxy
        is derived from this thermal signal and compared to BAS occupied status.
      </p>
      <div class="chart-box timeline">
        <canvas id="timelineChart"></canvas>
      </div>
    </section>

    <section class="two-col">
      <section class="panel">
        <h2>Hourly Profile: Actual vs Temp-Inferred Occupancy</h2>
        <p class="explain">
          This profile is used to produce the short-horizon occupancy and HVAC forecast.
        </p>
        <div class="chart-box hourly">
          <canvas id="hourlyChart"></canvas>
        </div>
      </section>
      <section class="panel">
        <h2>Forecast Horizon</h2>
        <p class="explain">
          Occupancy probability comes from projected cooling delta relative to the learned threshold.
          Recommended setbacks are generated where occupancy probability is low and expected HVAC kW is non-trivial.
        </p>
        <div class="chart-box forecast">
          <canvas id="forecastChart"></canvas>
        </div>
      </section>
    </section>

    <section class="panel">
      <h2>Top Recommended Setback Windows</h2>
      <div class="table-wrap">
        <table id="windowTable">
          <thead>
            <tr>
              <th>Start</th>
              <th>End</th>
              <th>Duration (h)</th>
              <th>Projected Savings (kWh)</th>
              <th>Mean HVAC kW</th>
              <th>Mean Occupancy Prob</th>
            </tr>
          </thead>
          <tbody></tbody>
        </table>
      </div>
      <p class="mono" id="windowEmpty" style="display:none; margin-top:0.6rem;">
        No windows passed the current thresholds. Lower `--opportunity-kw` or raise `--occ-prob-threshold`.
      </p>
    </section>

    <section class="panel">
      <h2>Assumptions and Signals</h2>
      <ul class="notes">
        <li>Occupied baseline label: any AHU occupied status equal to <code>AAAB</code>.</li>
        <li>Thermal feature: mean of AHU-01 and AHU-02 return-supply delta.</li>
        <li>Opportunity rule: predicted unoccupied and HVAC kW at/above configured threshold.</li>
        <li>Projected savings assumes configurable fractional load reduction during setback windows.</li>
      </ul>
      <p class="mono" id="columnMap"></p>
    </section>
  </main>

  <script>
    const payload = {payload_json};

    const fmt = (v, digits = 2) => {{
      if (v === null || v === undefined || Number.isNaN(v)) return "n/a";
      return Number(v).toLocaleString(undefined, {{
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }});
    }};

    const pct = (v) => (100 * Number(v)).toFixed(1) + "%";
    const asLocal = (iso) => new Date(iso).toLocaleString();

    const summary = payload.summary;
    const metrics = payload.model_metrics;
    const history = payload.historical;
    const forecast = payload.forecast;

    document.getElementById("chipRange").textContent = `${{summary.start}} -> ${{summary.end}}`;
    document.getElementById("chipRows").textContent = `${{summary.rows.toLocaleString()}} rows`;
    document.getElementById("chipStep").textContent = `${{summary.step_minutes.toFixed(0)}} min step`;
    document.getElementById("chipThreshold").textContent = `delta threshold: ${{fmt(metrics.threshold_f, 2)}} F`;

    document.getElementById("kpiAccuracy").textContent = pct(metrics.test.accuracy);
    document.getElementById("kpiBalanced").textContent = `balanced: ${{pct(metrics.test.balanced_accuracy)}}`;
    document.getElementById("kpiOppHours").textContent = fmt(history.opportunity_hours, 1);
    document.getElementById("kpiHistKwh").textContent = fmt(history.estimated_avoidable_kwh, 1);
    document.getElementById("kpiForecastHours").textContent = fmt(forecast.horizon_hours, 0);
    document.getElementById("kpiForecastKwh").textContent = fmt(forecast.projected_savings_kwh, 1);
    document.getElementById("kpiDeltaGap").textContent = fmt(summary.occupied_delta_mean_f - summary.unoccupied_delta_mean_f, 2);

    const columnMap = Object.entries(payload.column_map)
      .map(([k, v]) => `${{k}} = ${{v}}`)
      .join(" | ");
    document.getElementById("columnMap").textContent = columnMap;

    const timelineCtx = document.getElementById("timelineChart");
    new Chart(timelineCtx, {{
      type: "line",
      data: {{
        labels: payload.recent_timeline.labels,
        datasets: [
          {{
            label: "Cooling delta (F)",
            data: payload.recent_timeline.cooling_delta_f,
            yAxisID: "yDelta",
            borderColor: "#0b7285",
            backgroundColor: "rgba(11, 114, 133, 0.12)",
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.15
          }},
          {{
            label: "HVAC kW",
            data: payload.recent_timeline.hvac_kw,
            yAxisID: "yKw",
            borderColor: "#c2410c",
            backgroundColor: "rgba(194, 65, 12, 0.12)",
            borderWidth: 1.6,
            pointRadius: 0,
            tension: 0.18
          }},
          {{
            label: "Actual occupied (0/1)",
            data: payload.recent_timeline.occupied_actual,
            yAxisID: "yOcc",
            borderColor: "#2b8a3e",
            borderWidth: 1.2,
            pointRadius: 0,
            stepped: true
          }},
          {{
            label: "Temp-model occupied (0/1)",
            data: payload.recent_timeline.occupied_pred,
            yAxisID: "yOcc",
            borderColor: "#4f46e5",
            borderWidth: 1.1,
            pointRadius: 0,
            stepped: true
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        resizeDelay: 120,
        interaction: {{ mode: "index", intersect: false }},
        plugins: {{
          legend: {{ position: "top" }}
        }},
        scales: {{
          x: {{
            ticks: {{ maxTicksLimit: 12, autoSkip: true, maxRotation: 0 }},
            grid: {{ display: false }}
          }},
          yDelta: {{
            type: "linear",
            position: "left",
            title: {{ display: true, text: "Cooling delta (F)" }},
            grid: {{ color: "rgba(148, 163, 184, 0.2)" }}
          }},
          yKw: {{
            type: "linear",
            position: "right",
            title: {{ display: true, text: "HVAC kW" }},
            grid: {{ drawOnChartArea: false }}
          }},
          yOcc: {{
            type: "linear",
            position: "right",
            min: -0.05,
            max: 1.05,
            display: false,
            grid: {{ drawOnChartArea: false }}
          }}
        }}
      }}
    }});

    const hourlyCtx = document.getElementById("hourlyChart");
    new Chart(hourlyCtx, {{
      data: {{
        labels: payload.hourly_profile.hours,
        datasets: [
          {{
            type: "bar",
            label: "Mean HVAC kW",
            data: payload.hourly_profile.mean_hvac_kw,
            yAxisID: "yKw",
            backgroundColor: "rgba(194, 65, 12, 0.35)",
            borderColor: "#c2410c",
            borderWidth: 1
          }},
          {{
            type: "line",
            label: "Actual occupancy rate",
            data: payload.hourly_profile.actual_occ_rate,
            yAxisID: "yRate",
            borderColor: "#2b8a3e",
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.25
          }},
          {{
            type: "line",
            label: "Temp-model occupancy rate",
            data: payload.hourly_profile.pred_occ_rate,
            yAxisID: "yRate",
            borderColor: "#0b7285",
            borderWidth: 2,
            pointRadius: 2,
            tension: 0.25
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        resizeDelay: 120,
        plugins: {{ legend: {{ position: "top" }} }},
        scales: {{
          yRate: {{
            position: "left",
            min: 0,
            max: 1,
            ticks: {{
              callback: (value) => `${{Math.round(value * 100)}}%`
            }},
            title: {{ display: true, text: "Occupancy rate" }}
          }},
          yKw: {{
            position: "right",
            title: {{ display: true, text: "HVAC kW" }},
            grid: {{ drawOnChartArea: false }}
          }}
        }}
      }}
    }});

    const forecastCtx = document.getElementById("forecastChart");
    new Chart(forecastCtx, {{
      data: {{
        labels: payload.forecast.timeline_labels,
        datasets: [
          {{
            type: "bar",
            label: "Expected HVAC kW",
            data: payload.forecast.expected_hvac_kw,
            yAxisID: "yKw",
            backgroundColor: "rgba(148, 163, 184, 0.42)",
            borderWidth: 0
          }},
          {{
            type: "line",
            label: "Occupancy probability from temp",
            data: payload.forecast.occ_prob_from_temp,
            yAxisID: "yRate",
            borderColor: "#0b7285",
            backgroundColor: "rgba(11, 114, 133, 0.08)",
            borderWidth: 2,
            pointRadius: 0,
            tension: 0.2
          }},
          {{
            type: "line",
            label: "Setback recommended (0/1)",
            data: payload.forecast.setback_recommended,
            yAxisID: "yFlag",
            borderColor: "#b02a37",
            borderWidth: 1.2,
            pointRadius: 0,
            stepped: true
          }}
        ]
      }},
      options: {{
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        resizeDelay: 120,
        plugins: {{
          legend: {{ position: "top" }}
        }},
        scales: {{
          x: {{
            ticks: {{ maxTicksLimit: 9, autoSkip: true, maxRotation: 0 }},
            grid: {{ display: false }}
          }},
          yRate: {{
            position: "left",
            min: 0,
            max: 1,
            title: {{ display: true, text: "Occupancy probability" }},
            ticks: {{
              callback: (value) => `${{Math.round(value * 100)}}%`
            }}
          }},
          yKw: {{
            position: "right",
            title: {{ display: true, text: "Expected HVAC kW" }},
            grid: {{ drawOnChartArea: false }}
          }},
          yFlag: {{
            position: "right",
            min: -0.05,
            max: 1.05,
            display: false,
            grid: {{ drawOnChartArea: false }}
          }}
        }}
      }}
    }});

    const tbody = document.querySelector("#windowTable tbody");
    if (!payload.forecast.windows.length) {{
      document.getElementById("windowEmpty").style.display = "block";
    }} else {{
      for (const windowRec of payload.forecast.windows) {{
        const tr = document.createElement("tr");
        const cells = [
          asLocal(windowRec.start),
          asLocal(windowRec.end),
          fmt(windowRec.duration_hours, 2),
          fmt(windowRec.projected_savings_kwh, 2),
          fmt(windowRec.mean_hvac_kw, 2),
          pct(windowRec.mean_occ_prob)
        ];
        for (const value of cells) {{
          const td = document.createElement("td");
          td.textContent = value;
          tr.appendChild(td);
        }}
        tbody.appendChild(tr);
      }}
    }}
  </script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a demo-ready temperature-driven occupancy/control HTML report."
    )
    parser.add_argument(
        "--input",
        default="data/interim/brenhall_2024_hvac_combined.csv",
        help="Path to combined Bren Hall HVAC CSV",
    )
    parser.add_argument(
        "--output",
        default="demo/temp_poc_demo.html",
        help="Output HTML path",
    )
    parser.add_argument(
        "--json-output",
        default="",
        help="Optional payload JSON output path",
    )
    parser.add_argument(
        "--forecast-hours",
        type=int,
        default=168,
        help="Forecast horizon in hours for recommendation windows",
    )
    parser.add_argument(
        "--recent-days",
        type=int,
        default=14,
        help="Number of trailing days shown in the timeline chart",
    )
    parser.add_argument(
        "--opportunity-kw",
        type=float,
        default=0.5,
        help="Minimum residual HVAC kW to count as a control opportunity",
    )
    parser.add_argument(
        "--setback-reduction",
        type=float,
        default=0.30,
        help="Fractional HVAC reduction assumed during setback windows (0-1)",
    )
    parser.add_argument(
        "--occ-prob-threshold",
        type=float,
        default=0.35,
        help="Maximum occupancy probability to recommend setback",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    columns = pd.read_csv(input_path, nrows=0).columns.tolist()
    column_map = discover_columns(columns)

    usecols = list(dict.fromkeys(column_map.values()))
    raw = pd.read_csv(input_path, usecols=usecols, low_memory=False)
    raw["__timestamp"] = pd.to_datetime(raw[column_map["timestamp"]], errors="coerce")
    raw = raw.dropna(subset=["__timestamp"]).sort_values("__timestamp").reset_index(drop=True)

    df = pd.DataFrame()
    df["timestamp"] = raw["__timestamp"]

    df["occ_ahu1"] = raw[column_map["occ_ahu1"]].astype(str).str[:4]
    df["occ_ahu2"] = raw[column_map["occ_ahu2"]].astype(str).str[:4]
    df["occupied_actual"] = (df["occ_ahu1"] == ACTIVE_OCC_STATUS) | (
        df["occ_ahu2"] == ACTIVE_OCC_STATUS
    )

    return_temp_ahu1 = parse_numeric(raw[column_map["return_temp_ahu1"]])
    return_temp_ahu2 = parse_numeric(raw[column_map["return_temp_ahu2"]])
    supply_temp_ahu1 = parse_numeric(raw[column_map["supply_temp_ahu1"]])
    supply_temp_ahu2 = parse_numeric(raw[column_map["supply_temp_ahu2"]])
    df["hvac_kw"] = parse_numeric(raw[column_map["hvac_power_kw"]]).clip(lower=0)

    df["delta_ahu1_f"] = return_temp_ahu1 - supply_temp_ahu1
    df["delta_ahu2_f"] = return_temp_ahu2 - supply_temp_ahu2
    df["cooling_delta_f"] = df[["delta_ahu1_f", "delta_ahu2_f"]].mean(axis=1)
    df["return_temp_f"] = pd.concat([return_temp_ahu1, return_temp_ahu2], axis=1).mean(axis=1)
    df["supply_temp_f"] = pd.concat([supply_temp_ahu1, supply_temp_ahu2], axis=1).mean(axis=1)

    df = df.dropna(subset=["cooling_delta_f", "occupied_actual", "hvac_kw"]).reset_index(
        drop=True
    )
    if df.empty:
        raise ValueError("No valid rows found after parsing key columns.")

    step_hours = infer_step_hours(df["timestamp"])
    step_minutes = step_hours * 60.0

    split_idx = max(int(len(df) * 0.8), 1)
    train_df = df.iloc[:split_idx]
    test_df = df.iloc[split_idx:] if split_idx < len(df) else df.iloc[:0]

    threshold_f = select_threshold(train_df, "cooling_delta_f", "occupied_actual")
    df["occupied_pred"] = df["cooling_delta_f"] >= threshold_f

    metrics_train = compute_classification_metrics(
        train_df["occupied_actual"],
        train_df["cooling_delta_f"] >= threshold_f,
    )
    metrics_test = (
        compute_classification_metrics(
            test_df["occupied_actual"],
            test_df["cooling_delta_f"] >= threshold_f,
        )
        if not test_df.empty
        else metrics_train
    )
    metrics_all = compute_classification_metrics(df["occupied_actual"], df["occupied_pred"])

    df["opportunity"] = (~df["occupied_pred"]) & (df["hvac_kw"] >= float(args.opportunity_kw))
    df["avoidable_kwh"] = np.where(
        df["opportunity"],
        df["hvac_kw"] * step_hours * float(args.setback_reduction),
        0.0,
    )

    hourly_profile = (
        df.assign(hour=df["timestamp"].dt.hour)
        .groupby("hour")
        .agg(
            actual_occ_rate=("occupied_actual", "mean"),
            pred_occ_rate=("occupied_pred", "mean"),
            mean_hvac_kw=("hvac_kw", "mean"),
            mean_cooling_delta_f=("cooling_delta_f", "mean"),
            opportunity_rate=("opportunity", "mean"),
        )
        .reindex(range(24))
        .reset_index()
    )

    recent_cutoff = df["timestamp"].max() - pd.to_timedelta(int(args.recent_days), unit="D")
    recent = df.loc[df["timestamp"] >= recent_cutoff].copy()
    recent_chart = downsample_frame(recent, max_points=600)

    dow_hour_profile = (
        df.assign(
            day_of_week=df["timestamp"].dt.dayofweek,
            hour=df["timestamp"].dt.hour,
        )
        .groupby(["day_of_week", "hour"])
        .agg(
            expected_cooling_delta_f=("cooling_delta_f", "mean"),
            expected_hvac_kw=("hvac_kw", "mean"),
            occupancy_rate_actual=("occupied_actual", "mean"),
        )
        .reset_index()
    )

    forecast_steps = max(int(round(float(args.forecast_hours) / step_hours)), 1)
    forecast_start = df["timestamp"].max() + pd.to_timedelta(step_hours, unit="h")
    forecast_index = pd.date_range(
        start=forecast_start,
        periods=forecast_steps,
        freq=pd.to_timedelta(step_hours, unit="h"),
    )

    forecast_df = pd.DataFrame({"timestamp": forecast_index})
    forecast_df["day_of_week"] = forecast_df["timestamp"].dt.dayofweek
    forecast_df["hour"] = forecast_df["timestamp"].dt.hour
    forecast_df = forecast_df.merge(
        dow_hour_profile,
        how="left",
        on=["day_of_week", "hour"],
    )

    delta_scale = max(float(df["cooling_delta_f"].std()) / 4.0, 0.45)
    forecast_df["occ_prob_from_temp"] = 1.0 / (
        1.0 + np.exp(-(forecast_df["expected_cooling_delta_f"] - threshold_f) / delta_scale)
    )
    forecast_df["occ_prob_from_temp"] = forecast_df["occ_prob_from_temp"].clip(0.01, 0.99)
    forecast_df["setback_recommended"] = (
        (forecast_df["occ_prob_from_temp"] <= float(args.occ_prob_threshold))
        & (forecast_df["expected_hvac_kw"] >= float(args.opportunity_kw))
    )
    forecast_df["projected_savings_kwh"] = np.where(
        forecast_df["setback_recommended"],
        forecast_df["expected_hvac_kw"] * step_hours * float(args.setback_reduction),
        0.0,
    )
    forecast_chart = downsample_frame(forecast_df, max_points=500)

    windows = build_recommendation_windows(forecast_df, step_hours)

    summary = {
        "rows": int(len(df)),
        "start": str(df["timestamp"].min()),
        "end": str(df["timestamp"].max()),
        "step_minutes": step_minutes,
        "occupied_delta_mean_f": float(df.loc[df["occupied_actual"], "cooling_delta_f"].mean()),
        "unoccupied_delta_mean_f": float(
            df.loc[~df["occupied_actual"], "cooling_delta_f"].mean()
        ),
    }

    historical = {
        "opportunity_hours": float(df["opportunity"].sum() * step_hours),
        "estimated_avoidable_kwh": float(df["avoidable_kwh"].sum()),
        "opportunity_rate": float(df["opportunity"].mean()),
        "total_hvac_energy_kwh": float((df["hvac_kw"] * step_hours).sum()),
    }

    forecast_payload = {
        "horizon_hours": float(forecast_steps * step_hours),
        "projected_savings_kwh": float(forecast_df["projected_savings_kwh"].sum()),
        "timeline_labels": [ts.strftime("%m-%d %H:%M") for ts in forecast_chart["timestamp"]],
        "expected_hvac_kw": [
            None if pd.isna(v) else float(v) for v in forecast_chart["expected_hvac_kw"]
        ],
        "occ_prob_from_temp": [
            None if pd.isna(v) else float(v) for v in forecast_chart["occ_prob_from_temp"]
        ],
        "setback_recommended": [int(bool(v)) for v in forecast_chart["setback_recommended"]],
        "windows": windows,
    }

    payload = {
        "summary": summary,
        "column_map": column_map,
        "model_metrics": {
            "threshold_f": float(threshold_f),
            "train": metrics_train,
            "test": metrics_test,
            "all": metrics_all,
        },
        "historical": historical,
        "recent_timeline": {
            "labels": [ts.strftime("%m-%d %H:%M") for ts in recent_chart["timestamp"]],
            "cooling_delta_f": [float(v) for v in recent_chart["cooling_delta_f"]],
            "hvac_kw": [float(v) for v in recent_chart["hvac_kw"]],
            "occupied_actual": [int(v) for v in recent_chart["occupied_actual"]],
            "occupied_pred": [int(v) for v in recent_chart["occupied_pred"]],
        },
        "hourly_profile": {
            "hours": [f"{h:02d}:00" for h in hourly_profile["hour"]],
            "actual_occ_rate": [
                None if pd.isna(v) else float(v) for v in hourly_profile["actual_occ_rate"]
            ],
            "pred_occ_rate": [
                None if pd.isna(v) else float(v) for v in hourly_profile["pred_occ_rate"]
            ],
            "mean_hvac_kw": [
                None if pd.isna(v) else float(v) for v in hourly_profile["mean_hvac_kw"]
            ],
            "mean_cooling_delta_f": [
                None if pd.isna(v) else float(v)
                for v in hourly_profile["mean_cooling_delta_f"]
            ],
            "opportunity_rate": [
                None if pd.isna(v) else float(v)
                for v in hourly_profile["opportunity_rate"]
            ],
        },
        "forecast": forecast_payload,
        "config": {
            "opportunity_kw": float(args.opportunity_kw),
            "setback_reduction": float(args.setback_reduction),
            "occ_prob_threshold": float(args.occ_prob_threshold),
            "forecast_hours": int(args.forecast_hours),
            "recent_days": int(args.recent_days),
        },
    }

    html = build_html(payload, "Bren Hall Temperature-Control Proof of Concept")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    if args.json_output:
        json_path = Path(args.json_output)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Demo written: {output_path.resolve()}")
    print(f"Rows analyzed: {summary['rows']:,}")
    print(f"Range: {summary['start']} -> {summary['end']}")
    print(f"Threshold (cooling delta): {threshold_f:.2f} F")
    print(
        "Test accuracy: "
        f"{metrics_test['accuracy'] * 100:.2f}% "
        f"(balanced {metrics_test['balanced_accuracy'] * 100:.2f}%)"
    )
    print(
        "Historical opportunity: "
        f"{historical['opportunity_hours']:.1f} h, "
        f"{historical['estimated_avoidable_kwh']:.1f} kWh estimated avoidable"
    )
    print(
        "Forecast projected savings: "
        f"{forecast_payload['projected_savings_kwh']:.1f} kWh "
        f"over {forecast_payload['horizon_hours']:.0f} h"
    )


if __name__ == "__main__":
    main()
