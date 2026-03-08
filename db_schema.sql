create table user_ap_trajectory
(
    "user"       varchar(255) not null,
    access_point varchar(255) not null,
    beginning    timestamp    not null,
    "end"        timestamp    not null,
    primary key ("user", access_point, beginning, "end")
);

alter table user_ap_trajectory
    owner to dcgroup;

create index idx_user
    on user_ap_trajectory ("user");

create index idx_access_point
    on user_ap_trajectory (access_point);

create index idx_beginning
    on user_ap_trajectory (beginning);

create index idx_end
    on user_ap_trajectory ("end");

create table "user_location_trajectory_FINE_V2"
(
    "user"    varchar(255) not null,
    space_id  integer      not null,
    beginning timestamp    not null,
    "end"     timestamp    not null,
    primary key ("user", space_id, beginning, "end")
);

alter table "user_location_trajectory_FINE_V2"
    owner to dcgroup;

create index idx_space_id
    on "user_location_trajectory_FINE_V2" (space_id);

create index idx_ultf_v2_user
    on "user_location_trajectory_FINE_V2" ("user");

create index idx_ultf_v2_space_id
    on "user_location_trajectory_FINE_V2" (space_id);

create index idx_ultf_v2_beginning
    on "user_location_trajectory_FINE_V2" (beginning);

create index idx_ultf_v2_end
    on "user_location_trajectory_FINE_V2" ("end");

create table observation_merged
(
    payload     varchar(255) not null,
    "timeStamp" timestamp    not null,
    sensor_id   varchar(255) not null,
    primary key (payload, "timeStamp", sensor_id)
);

alter table observation_merged
    owner to dcgroup;

create index idx_obs_merged_payload
    on observation_merged (payload);

create index idx_obs_merged_timestamp
    on observation_merged ("timeStamp");

create index idx_obs_merged_sensor_id
    on observation_merged (sensor_id);

create table region_to_coverage
(
    region_id               integer          not null,
    space_name              varchar(200)     not null,
    wapcov_id               integer          not null,
    sensor                  varchar(200)     not null,
    intersection_percentage double precision not null,
    primary key (region_id, space_name, wapcov_id, sensor, intersection_percentage)
);

alter table region_to_coverage
    owner to dcgroup;

create index idx_rtc_region_id
    on region_to_coverage (region_id);

create index idx_rtc_space_name
    on region_to_coverage (space_name);

create index idx_rtc_wapcov_id
    on region_to_coverage (wapcov_id);

create index idx_rtc_sensor
    on region_to_coverage (sensor);

create index idx_rtc_intersection
    on region_to_coverage (intersection_percentage);

create table space_metadata
(
    "roomID"      integer      not null,
    "typeID"      integer      not null,
    type          varchar(200) not null,
    building_room varchar(200) default NULL::character varying,
    primary key ("roomID", "typeID", type)
);

alter table space_metadata
    owner to dcgroup;

create index idx_sm_roomid
    on space_metadata ("roomID");

create index idx_sm_typeid
    on space_metadata ("typeID");

create index idx_sm_type
    on space_metadata (type);

create index idx_sm_building_room
    on space_metadata (building_room);

create table space
(
    space_id        integer not null
        primary key,
    space_name      varchar(200) default NULL::character varying,
    parent_space_id integer,
    building_room   varchar(200) default NULL::character varying
);

alter table space
    owner to dcgroup;

create index idx_spc_space_id
    on space (space_id);

create index idx_spc_space_name
    on space (space_name);

create index idx_spc_parent_space_id
    on space (parent_space_id);

create index idx_spc_building_room
    on space (building_room);

create table space_occupancy
(
    space_id  integer   not null,
    occupancy integer   not null,
    beginning timestamp not null,
    "end"     timestamp not null,
    primary key (space_id, occupancy, beginning, "end")
);

alter table space_occupancy
    owner to dcgroup;

create index idx_occ_occupancy
    on space_occupancy (occupancy);

create index idx_occ_space_id
    on space_occupancy (space_id);

create index idx_occ_beginning
    on space_occupancy (beginning);

create index idx_occ_end
    on space_occupancy ("end");

create table hvac
(
    timestamp timestamp,
    space_id  text,
    zone_temp double precision
);

alter table hvac
    owner to dcgroup;

create table wifi_data
(
    timestamp timestamp,
    mac       text,
    wap       text
);

alter table wifi_data
    owner to dcgroup;


