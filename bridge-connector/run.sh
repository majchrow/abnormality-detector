if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

source.env
bridge-connector --addresses host1:port1 host2:port2 --logfile logs/logfile.json --kafka-file logs/kafka_file.json --dumpfile logs/dumpfile.json
