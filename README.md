*Steps to set up agent*

1) **Set up virtual environment**: 
```bash
python3 -m venv venv
source venv/bin/activate
```

2) **Install all requirements**: 
```bash
pip install -r requirements.txt
```

3) **Fill in env file**: Create a `.env` file with the following:
```
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=INSERT!
LANGCHAIN_PROJECT=INSERT!
OPENAI_API_KEY=INSERT
```

4) **Run the agent**: 
```bash
python agent.py
```