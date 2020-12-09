CREATE KEYSPACE test WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 1}; 
USE test; 

CREATE TABLE roster_update(
    meeting_name text,
    datetime timestamp,
    initial int, 
    ringing int, 
    connected int, 
    onhold int, 
    active_speaker int, 
    presenter int, 
    endpoint_recording int, 
    hour int, 
    week_day_number int,
    anomaly boolean,
    anomaly_reason text,
    ml_anomaly boolean,
    ml_anomaly_reason text,
    start_datetime timestamp,
    PRIMARY KEY (meeting_name, datetime)
); 

CREATE TABLE calls(
    start_datetime timestamp,
    last_update timestamp,
    meeting_name text,
    duration int,
    finished boolean,
    PRIMARY KEY (meeting_name, start_datetime)
);

CREATE TABLE call_info_update(
    meeting_name text,
    datetime timestamp,
    adhoc boolean, 
    cospace boolean, 
    current_participants int, 
    forwarding boolean, 
    hour int, 
    locked boolean, 
    lync_conferencing boolean, 
    max_participants int, 
    mean_participants double, 
    recording boolean, 
    streaming boolean, 
    time_diff bigint, 
    week_day_number int,
    anomaly boolean,
    anomaly_reason text, 
    ml_anomaly boolean,
    ml_anomaly_reason text,
    start_datetime timestamp,
    PRIMARY KEY (meeting_name, datetime)
);

CREATE TABLE meetings(
    meeting_name text PRIMARY KEY, 
    meeting_number text,
    criteria text,
    monitored boolean,
    anomaly_monitored boolean
);

CREATE TABLE models(
    meeting_name text,
    model_id text,
    description text,
    model blob,
    PRIMARY KEY (meeting_name, model_id)
);

CREATE TABLE inference_jobs(
    meeting_name text,
    start_datetime timestamp,
    end_datetime timestamp,
    model_id text,
    completed boolean,
    PRIMARY KEY ((meeting_name, model_id), end_datetime)
);

CREATE TABLE locks(
    resource_name text PRIMARY KEY,
    lock_id text
);

