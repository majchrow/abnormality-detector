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
    ml_anomaly_reason text,
    threshold double,
    start_datetime timestamp,
    PRIMARY KEY (meeting_name, datetime)
) WITH default_time_to_live = 2592000 AND gc_grace_seconds = 3600; 

CREATE TABLE calls(
    start_datetime timestamp,
    last_update timestamp,
    meeting_name text,
    duration int,
    finished boolean,
    anomaly boolean,
    anomaly_reason text,
    PRIMARY KEY (meeting_name, start_datetime)
) WITH default_time_to_live = 2592000 AND gc_grace_seconds = 3600; 

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
    ml_anomaly_reason text,
    threshold double,
    start_datetime timestamp,
    PRIMARY KEY (meeting_name, datetime)
) WITH default_time_to_live = 2592000 AND gc_grace_seconds = 3600; 

CREATE TABLE meetings(
    meeting_name text PRIMARY KEY, 
    meeting_number text,
    criteria text,
    monitored boolean,
    ml_monitored boolean
);

CREATE TABLE training_jobs(
    job_id text PRIMARY KEY,
    meeting_name text,
    submission_datetime timestamp,
    training_call_starts list<timestamp>,
    threshold double,
    status text
);

CREATE TABLE models(
    meeting_name text PRIMARY KEY,
    training_call_starts list<timestamp>,
    threshold double,
    call_info_model blob,
    roster_model blob
);

CREATE TABLE inference_jobs(
    meeting_name text,
    start_datetime timestamp,
    end_datetime timestamp,
    status text,
    PRIMARY KEY (meeting_name, end_datetime)
) WITH default_time_to_live = 3600;

CREATE TABLE locks(
    resource_name text PRIMARY KEY,
    lock_id text,
    last_locked timestamp
) WITH default_time_to_live = 30;

