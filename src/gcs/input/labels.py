PS4_TABLE = {
    "buttons": {
        0: "square",
        1: "cross",
        2: "circle",
        3: "triangle",
        4: "l1",
        5: "r1",
        6: "l2",
        7: "r2",
        8: "share",
        9: "options",
        10: "l3",
        11: "r3",
        12: "ps",
        13: "touchpad",
    },
    "axes": {"leftx": "x", "lefty": "y", "rightx": "z", "righty": "rz"},
}

GENERIC_TABLE = {
    "buttons": {},
    "axes": {"leftx": "x", "lefty": "y", "rightx": "rx", "righty": "ry"},
}

PLAYSTATION_WORDS = (
    "ps3",
    "ps4",
    "ps5",
    "dualshock",
    "dualsense",
    "playstation",
    "wireless controller",
)


def table_for(controller_name):
    """Pick the mapping table that matches the controller's model name."""
    lowered = controller_name.lower()
    if any(word in lowered for word in PLAYSTATION_WORDS):
        return PS4_TABLE
    return GENERIC_TABLE