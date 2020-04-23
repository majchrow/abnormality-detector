if [[ ! -d ".venv" ]]
then
	python3 -m venv .venv
fi


python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
deactivate