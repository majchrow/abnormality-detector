CREATE KEYSPACE test WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 1}; 
USE test; 

CREATE TABLE roster_update(
meeting_name text,
datetime timestamp,
call_id text,
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
PRIMARY KEY (meeting_name, datetime)); 

CREATE TABLE call_info_update(
meeting_name text,
datetime timestamp,
call_id text,
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
PRIMARY KEY (meeting_name, datetime));

CREATE TABLE calls(
meeting_name text,
start_datetime timestamp,
last_update timestamp,
finished boolean,
PRIMARY KEY (meeting_name, start_datetime));

CREATE TABLE meetings(
meeting_name text PRIMARY KEY, 
meeting_number text,
criteria text,
monitored boolean);

