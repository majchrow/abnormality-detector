if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt

echo 'Running client'
python3 main.py --host host --port 443 --logfile logfile
