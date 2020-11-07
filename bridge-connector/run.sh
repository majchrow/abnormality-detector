if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

echo 'Running client'
bridge-connector --addresses cbr-01.mche.edu.pl:445 --logfile client_log_multi_sane.json

