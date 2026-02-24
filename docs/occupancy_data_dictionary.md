# Occupancy Data Dictionary

Generated from `data/raw/occupancy/brenhall_ap_15min/*.csv`.

## Dataset Summary

- Rows: **1,862,847**
- Columns: **4**
- Source files: **4**
- Time range: **2017-03-31 15:00:00 -> 2019-05-20 12:00:00**

## Schema

| Column | Dtype | Null % | Unique | Meaning | Example |
|---|---:|---:|---:|---|---|
| access_point | object | 0.0000% | 63 | access-point identifier | 3146-clwa-6122 ,  3141-clwa-1100 ,  3141-clwa-1200 |
| interval_begin | datetime64[ns] | 0.0000% | 49706 | time bucket start | 2017-03-31 15:00:00 ,  2017-08-28 16:00:00 ,  2017-08-28 16:00:00 |
| count | int64 | 0.0000% | 273 | observed occupancy count | 1 ,  4 ,  10 |
| source_file | object | 0.0000% | 4 | source filename | ap_occupancy_15min_raw.csv ,  ap_occupancy_15min_raw.csv ,  ap_occupancy_15min_raw.csv |

## Notes

- Raw source schemas were normalized to: `access_point`, `interval_begin`, `count`.

- `interval_begin_time` and `ap` are mapped to canonical names when present.

- `count` is coerced to numeric for analysis readiness.
