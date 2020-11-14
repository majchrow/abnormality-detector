### Setup 
Trzeba zainstalować pakiet `connector`, najlepiej w nowym virtualenvie.
 1. `python3 -m venv .venv`
 2. `source .venv/bin/activate`
 3. `pip install --upgrade pip`
 4. `pip install -r requirements.txt`
 
 Wymaga co najmniej Pythona 3.8.
 
### Uruchomienie

 1. `source .env`
 2. <code>bridge-connector --addresses host1:port1 host2:port2 ... <br>
 &nbsp; --logfile logs/client_log.json <br>
 &nbsp; --dumpfile logs/client_dump.json <br>
 &nbsp; --kafka-bootstrap-server localhost:9092 <br>
 &nbsp; --kafka-file logs/kafka_dump.json</code>

W tym momencie logi serwera idą do `logfile`, do `dumpfile` idą surowe wiadomości serwera, potem może z nich 
korzystać serwer testowy. `kafka-file` i `kafka-bootstrap-server` są opcjonalne i określają gdzie mają trafić
wiadomości przeznaczone do preprocessingu.


### Testy

Odpalamy najpierw serwer testowy przez `python test/server.py` (wymagane są zmienne środowiskowe 
`BRIDGE_USERNAME` i `BRIDGE_PASSWORD`), potem `bridge-connector` jak wyżej, podając adres serwera testowego
i dodatkowo opcję `no-ssl` (przykład w skrypcie `run.sh`).
