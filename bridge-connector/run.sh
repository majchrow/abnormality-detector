if [[ ! -d ".venv" ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt
echo 'Running server'
python3 main.py &
sleep 3
echo 'Running client'
python3 main.py --client
sleep 3
killall python3
deactivate
