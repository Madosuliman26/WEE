# WEE
ROV training code

# ROV Ground Control Station

AAST Triton ROVs software training. Headless Phase 1: event bus, configuration
and operator input (controller + keyboard).

## Setup (Windows PowerShell)

```
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

```
python -m gcs.main
```

## Tests and lint

```
pytest
ruff check .
```

## Project layout

- `config/` - settings.json and profiles.json
- `src/gcs/core/` - event bus, events, config manager, logging setup
- `src/gcs/input/` - controller, keyboard, profiles, input service
- `tests/` - pytest tests
- `logs/` - rotating log files (not in Git)

## Configuration

All settings (rates, dead-zones, logging) live in `config/settings.json`.
Nothing is hard-coded in the source.