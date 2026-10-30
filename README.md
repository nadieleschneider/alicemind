# AliceMind

AliceMind is a local Streamlit assistant for chat, document analysis, task
management, and authorized project workflows. It connects to an OpenAI-compatible
chat endpoint such as OmniRoute.

## Requirements

- Windows
- Python 3.14
- An OpenAI-compatible chat service, such as a locally running OmniRoute

## Run from source

```powershell
python -m pip install -r requirements-build.txt
$env:OMNI_API_URL = "http://localhost:20128/v1/chat/completions"
$env:OMNI_API_KEY = "your-key-if-required"
python -m streamlit run app.py
```

Set `TAVILY_API_KEY` if you want to enable web search. Do not put API keys in
source files, Streamlit configuration, screenshots, or commits.

## Local data and privacy

Conversations, profile details, indexed documents, and other app data are stored
locally. Do not commit `.omni_memory/`, databases, `.env` files, or Streamlit
secrets. The project `.gitignore` excludes these files, build output, and
executables.

When a user sends a prompt or document for analysis, the app sends that content
to the configured AI endpoint. Review that service's privacy policy before
sending personal or confidential information.

## Tests

```powershell
python -m unittest discover -s tests
```

## Windows executable

Run `build_exe.ps1` to build the Windows application. See [EXECUTAVEL.md](EXECUTAVEL.md)
for details.

## License

This project is distributed under the MIT License. See [LICENSE](LICENSE).
