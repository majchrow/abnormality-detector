if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

echo 'Running client'
bridge-connector --addresses cbr-01.mche.edu.pl:445 cbr-02.mche.edu.pl:445 cbr-03.mche.edu.pl:445 cbr-04.mche.edu.pl:445 --logfile logs/log_sane_4_servers.json --kafka-file logs/kafka_4_servers.json --dumpfile logs/dump_4_servers.json
