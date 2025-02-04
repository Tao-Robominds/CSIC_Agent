# Donnie
Multi-Agent Business Automation on WhatsApp. 

## Luanch
- uvicorn backend.api.webhook:DONNIE --reload --port 8000
- ngrok http --url donnie.ngrok.app 8000
- streamlit run frontend/Donnie.py