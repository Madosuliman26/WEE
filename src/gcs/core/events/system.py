class Shutdown:
    pass


class ProfileChanged:
    def __init__(self, profile, reason):
        self.profile = profile
        self.reason = reason     # "auto", "manual" or "file_edit"


class ConfigReloaded:
    def __init__(self, changed_keys):
        self.changed_keys = changed_keys