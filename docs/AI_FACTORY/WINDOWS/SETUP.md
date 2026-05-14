# Windows Setup

> Windows support is desired but lower priority than the primary Python/Linux workflow.

## Current expectation

The repository is Python-first. Windows development should use a normal Python environment and the same package/test commands where possible.

## Suggested setup

1. Install Python 3.9+.
2. Open PowerShell in the repo root.
3. Create and activate a venv.
4. Install editable dependencies.

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
pip install -e ".[dev]"
pytest
```

## Visual Studio note

Visual Studio support is desirable for downstream engine integration work, but it is **low priority** for this repository unless a task is specifically about integration tooling. Do not restructure the repo around Visual Studio-only workflows.
