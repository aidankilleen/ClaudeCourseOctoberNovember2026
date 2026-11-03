# api-investigation

A scratch folder for trying out the Claude API directly, rather than through
Claude Code. Nothing else in this repository depends on it.

## Setting up

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:ANTHROPIC_API_KEY = "sk-ant-..."     # from https://console.anthropic.com
```

The key is read from the environment, never from the code, so it cannot be
committed by accident. It lasts only for the current PowerShell window.

## Running

```powershell
python hello_claude.py
python hello_claude.py "Explain SQLite to someone who has never programmed"
```

The script asks Claude one question and prints the answer, along with the
number of tokens the call used. Calls cost money - a question like the ones
above costs a fraction of a cent.

## Things to try

- Change `MODEL` in `hello_claude.py` to `claude-haiku-5-5` and notice the
  speed and the price difference.
- Change the `system` text and ask the same question again.
