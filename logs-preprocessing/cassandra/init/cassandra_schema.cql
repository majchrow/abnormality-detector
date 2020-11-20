CREATE KEYSPACE test WITH REPLICATION = {'class': 'SimpleStrategy', 'replication_factor': 1}; 
USE test; 
CREATE TABLE roster_update(datetime timestamp, 
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
name text, 
anomaly boolean,
reason text
PRIMARY KEY (call_id, datetime)); 
CREATE TABLE call_info_update(adhoc boolean, 
call_id text, 
cospace boolean, 
current_participants int, 
datetime timestamp, 
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
name text,
anomaly boolean,
reason text
PRIMARY KEY (call_id, datetime));
CREATE TABLE calls(call_id text PRIMARY KEY,
start_datetime timestamp,
last_update timestamp,
name text,
finished boolean);
CREATE TABLE meetings(
meeting_name text PRIMARY KEY, 
criteria text,
monitored boolean);
