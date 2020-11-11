if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

echo 'Running client'
bridge-connector --addresses host1:port1 host2:port2 --logfile logs/log_sane_4_servers.json --kafka-file logs/kafka_4_servers.json --dumpfile logs/dump_4_servers.json
