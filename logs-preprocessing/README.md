# Preprocessing - callInfoUpdate (tabela `call_info_update`)
Pola na wyjściu:
- Czas od rozpoczęcia spotkania -> time_diff
- Spotkanie nagrywane -> recording
- Spotkanie streamowane -> streaming
- Spotkanie zablokowane -> locked
- Spotkanie adHoc -> adhoc
- Spotkanie cospace -> cospace
- Spotkanie lync_conferencing -> lync_conferencing
- Spotkanie forwarding -> forwarding
- Aktualna liczba uczestników -> current_participants
- Średnia liczba uczestników w danym spotkaniu -> mean_participants
- Maksymalna liczba uczestników danego spotkania -> max_participants
- Czas rzeczywisty -> datetime
- Godzina -> hour
- Dzień tygodnia -> week_day_number
- Nazwa spotkania/pokoju -> name
- ID spotkania -> call_id

# Preprocessing - rosterUpdate (tabela `roster_update`)
Pola na wyjściu:
- Liczba uczestników w stanie initial -> initial
- Liczba uczestników w stanie ringing -> ringing
- Liczba uczestników w stanie connected -> connected
- Liczba uczestników w stanie onHold -> onhold
- Liczba uczestników z audioMuted -> audiomuted (muszę dodać)
- Liczba uczestników z videoMuted -> videomuted (muszę dodać)
- Liczba uczestników z activeSpeaker -> activespeaker
- Liczba uczestników presenter -> presenter
- Liczba uczestników endpointRecording -> endpoint_recording
- Czas rzeczywisty -> datetime
- Godzina -> hour
- Dzień tygodnia -> week_day_number
- Nazwa spotkania/pokoju -> name
- ID spotkania -> call_id

# Preprocessing - callListUpdate (tabela `calls`)
Pola na wyjściu:
- Czas rzeczywisty -> datetime
- Nazwa spotkania/pokoju -> name
- ID spotkania -> call_id
- Informacja, czy spotkanie się zakończyło -> finished

# Kafka
W katalogu logs-preprocessing/kafka/resources należy umieścić plik JSON (data.json) z danymi, które mają być wrzucane do kafki.

# Cassandra
Wewnątrz kontenera wykonujemy komendę cqlsh -u cassandra -p cassandra.
Do dyspozycji mamy keyspace o nazwie `test` oraz tabele `call_info_update`, `roster_update` i `calls`.
Jeśli chcemy wylistować dane np. z tabeli `calls`, to wpisujemy:
- `use test;`
- `select * from calls;`