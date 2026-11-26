# ROV Ground Control Station - Phase 1

AAST Triton ROVs software training. Phase 1 is a headless skeleton: an event bus,
a configuration system and operator input (game controller and keyboard).
There is no network, video or GUI yet.

## What it does

- Reads a game controller (axes, buttons, D-pad) and the keyboard (key down and key up).
- Samples input 50 times a second (configurable) in its own thread.
- Survives the controller being unplugged and replugged, and also starts with no controller.
- Keeps named mapping profiles in `config/profiles.json`, loads the right one when a known
  controller connects, and applies edits to the file without a restart.
- Publishes everything as events on a queued event bus.

## Setup (Windows PowerShell)

```
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

## Run

From the project root:

```
python -m gcs.main
```

Press Ctrl+C to stop. Logs go to the console and to `logs/gcs.log`.

## Tests and lint

```
pytest
ruff check .
```

Hardware checks that cannot be automated are listed in `docs/MANUAL_TESTS.md`.

## Configuration

Nothing is hard-coded. Everything lives in `config/`.

`config/settings.json`:

| Key | Meaning |
|---|---|
| `input.rate_hz` | Sampling rate of the input thread |
| `input.default_deadzone` | How far an axis must be pushed to count as -1 or 1 (0 to 1) |
| `logging.level` | DEBUG, INFO, WARNING, ERROR or CRITICAL |
| `logging.file`, `max_bytes`, `backup_count` | Rotating log file settings |
| `bus.queue_size` | Maximum number of waiting events |

`config/profiles.json`: named profiles that map input names to action names, a
`controller_map` that links a controller's model name to a profile, and a
`default_profile`.

## Input values

- Axes are direction only: -1, 0 or 1 (inside the dead-zone is 0).
- L2 and R2 are reported as buttons.
- The D-pad is reported as the buttons `dpup`, `dpdown`, `dpleft`, `dpright`.
- Controller buttons use readable names per model (for example `cross` on a PS4 pad).

## Controller support

- Tested with a PS4 pad ("Wireless Controller" on Windows). Its button numbers were
  measured with `experiments/map_controller.py` and `experiments/map_axes.py`.
- Other pads fall back to a generic table that is unverified (buttons are named
  `button0`, `button1`, ...).
- Windows only. On Windows pyglet hides Xbox (XInput) pads from the raw joystick
  API, so an Xbox pad is probably not detected without extra code.

## Events

| Event | Published when |
|---|---|
| `ControllerConnected(name)` | A controller appears |
| `ControllerDisconnected(name)` | The controller is unplugged |
| `ButtonPressed(button)` / `ButtonReleased(button)` | A controller button changes |
| `AxesChanged(axes)` | Any axis direction changes (`{}` when no controller) |
| `KeyDown(key)` / `KeyUp(key)` | A keyboard key changes |
| `ProfileChanged(profile, reason)` | The active profile changes (load, auto, file_edit, edited, manual) |
| `ConfigReloaded(changed_keys)` | Settings were reloaded |
| `Shutdown()` | The program is shutting down |

## Project layout

```
config/            settings.json, profiles.json
docs/              requirements table, manual tests, retrospective
temp/       throw-away scripts used to measure the controller
src/gcs/core/      event bus, events, config manager, logging setup
src/gcs/input/     controller, keyboard, labels, profiles, input service
src/gcs/main.py    wires everything together
tests/             pytest tests
logs/              rotating logs (not in Git)
```

Dependency rule: `core` imports nothing from the project, `input` imports only
`core` and itself. `tests/test_architecture.py` checks this.

## Threads

| Thread | Job |
|---|---|
| main | Starts everything, checks the profiles file, handles Ctrl+C |
| `input` | Polls devices at the configured rate and publishes events |
| `bus` | Delivers queued events to subscribers |
| pynput listener | Collects key presses for the keyboard |

Threads talk only through `queue.Queue`, `threading.Event` and `threading.Lock`.
Multiprocessing is planned for video decoding in a later phase.

## Known limitations

- The profile mapping is loaded and kept live, but no code turns input names into
  actions yet.
- The generic controller table is unverified.
- Windows only.