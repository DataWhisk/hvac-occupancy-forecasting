# Database Data Dictionary

Generated from PostgreSQL metadata (`information_schema` + `pg_catalog`).

- Tables discovered: **9**

## hvac

- Estimated rows: **2,846,750**

| Column | Type | Nullable | Meaning | Comment |
|---|---|---|---|---|
| timestamp | timestamp without time zone | YES | time boundary / observation timestamp |  |
| space_id | text | YES | entity identifier |  |
| zone_temp | double precision | YES | temperature measurement |  |

## observation_merged

- Estimated rows: **21,608,349**

| Column | Type | Nullable | Meaning | Comment |
|---|---|---|---|---|
| payload | character varying | NO | raw payload or event value |  |
| timeStamp | timestamp without time zone | NO | time boundary / observation timestamp |  |
| sensor_id | character varying | NO | network/sensor source identifier |  |

## region_to_coverage

- Estimated rows: **208**

| Column | Type | Nullable | Meaning | Comment |
|---|---|---|---|---|
| region_id | integer | NO | entity identifier |  |
| space_name | character varying | NO | domain-specific field; confirm with data owner |  |
| wapcov_id | integer | NO | entity identifier |  |
| sensor | character varying | NO | network/sensor source identifier |  |
| intersection_percentage | double precision | NO | domain-specific field; confirm with data owner |  |

## space

- Estimated rows: **953**

| Column | Type | Nullable | Meaning | Comment |
|---|---|---|---|---|
| space_id | integer | NO | entity identifier |  |
| space_name | character varying | YES | domain-specific field; confirm with data owner |  |
| parent_space_id | integer | YES | hierarchical parent reference |  |
| building_room | character varying | YES | domain-specific field; confirm with data owner |  |

## space_metadata

- Estimated rows: **156**

| Column | Type | Nullable | Meaning | Comment |
|---|---|---|---|---|
| roomID | integer | NO | entity identifier |  |
| typeID | integer | NO | entity identifier |  |
| type | character varying | NO | domain-specific field; confirm with data owner |  |
| building_room | character varying | YES | domain-specific field; confirm with data owner |  |

## space_occupancy

- Estimated rows: **4,538,846**

| Column | Type | Nullable | Meaning | Comment |
|---|---|---|---|---|
| space_id | integer | NO | entity identifier |  |
| occupancy | integer | NO | observed occupancy count |  |
| beginning | timestamp without time zone | NO | time boundary / observation timestamp |  |
| end | timestamp without time zone | NO | time boundary / observation timestamp |  |

## user_ap_trajectory

- Estimated rows: **8,156,084**

| Column | Type | Nullable | Meaning | Comment |
|---|---|---|---|---|
| user | character varying | NO | anonymized user/device identifier |  |
| access_point | character varying | NO | network/sensor source identifier |  |
| beginning | timestamp without time zone | NO | time boundary / observation timestamp |  |
| end | timestamp without time zone | NO | time boundary / observation timestamp |  |

## user_location_trajectory_FINE_V2

- Estimated rows: **5,978,498**

| Column | Type | Nullable | Meaning | Comment |
|---|---|---|---|---|
| user | character varying | NO | anonymized user/device identifier |  |
| space_id | integer | NO | entity identifier |  |
| beginning | timestamp without time zone | NO | time boundary / observation timestamp |  |
| end | timestamp without time zone | NO | time boundary / observation timestamp |  |

## wifi_data

- Estimated rows: **873,333**

| Column | Type | Nullable | Meaning | Comment |
|---|---|---|---|---|
| timestamp | timestamp without time zone | YES | time boundary / observation timestamp |  |
| mac | text | YES | anonymized user/device identifier |  |
| wap | text | YES | network/sensor source identifier |  |
