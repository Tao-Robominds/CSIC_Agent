# CSIC Agent
Multi-Agent Smart Infrastructure System

# Environment
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip

pip install -r requirements.txt
pip install langgraph-cli[inmem]

langgraph dev

## Ngrok
- uvicorn backend.api.webhook:DONNIE --reload --port 8000
- ngrok http --url donnie.ngrok.app 8000
- streamlit run frontend/Donnie.py

