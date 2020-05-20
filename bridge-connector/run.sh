if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt
echo 'Running server'
python3 main.py --server &
sleep 3
echo 'Running client'
python3 main.py --auth_token empty
sleep 3
killall python3
deactivate
