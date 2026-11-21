from dataclasses import dataclass


@dataclass
class ControllerConnected:
    name: str
    instance_id: int


@dataclass
class ControllerDisconnected:
    name: str
    instance_id: int


@dataclass
class ProfileChanged:
    profile: str
    reason: str          # "auto", "manual" or "file_edit"


@dataclass
class ConfigReloaded:
    changed_keys: list


@dataclass
class Shutdown:
    pass


@dataclass
class InputState:
    timestamp: float
    controller: dict | None
    keys: list
    actions: dict