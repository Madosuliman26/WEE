import time

import pyglet

loop = pyglet.app.platform_event_loop
loop.start()

joystick = pyglet.input.get_joysticks()[0]
joystick.open()
print("controller:", joystick.device.name)

AXES = ("x", "y", "z", "rx", "ry", "rz")


def pump():
    pyglet.clock.tick()
    loop.step(0.001)
    time.sleep(0.005)


def record(seconds=3):
    low = {a: 9.0 for a in AXES}
    high = {a: -9.0 for a in AXES}
    hats = set()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        pump()
        for a in AXES:
            value = getattr(joystick, a)
            low[a] = min(low[a], value)
            high[a] = max(high[a], value)
        hats.add((joystick.hat_x, joystick.hat_y))
    print("   axes:", "  ".join(f"{a} {low[a]:+.2f}..{high[a]:+.2f}" for a in AXES))
    print("   hat values seen:", sorted(hats))


steps = [
    "DON'T TOUCH anything (rest)",
    "push the LEFT stick fully RIGHT and hold",
    "push the LEFT stick fully LEFT and hold",
    "push the LEFT stick fully UP and hold",
    "push the LEFT stick fully DOWN and hold",
    "push the RIGHT stick fully RIGHT and hold",
    "push the RIGHT stick fully UP and hold",
    "press D-pad UP and hold",
    "press D-pad DOWN and hold",
    "press D-pad LEFT and hold",
    "press D-pad RIGHT and hold",
]

for step in steps:
    input(f"\nPress Enter, THEN: {step} (3 seconds) ")
    record()