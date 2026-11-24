class ControllerConnected:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"ControllerConnected(name={self.name})"


class ControllerDisconnected:
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f"ControllerDisconnected(name={self.name})"


class AxesChanged:
    def __init__(self, axes):
        self.axes = axes


class ButtonPressed:
    def __init__(self, button):
        self.button = button
    def __repr__(self):
        return f"Button Pressed (button={self.button})"


class ButtonReleased:
    def __init__(self,button):
        self.button=button
    def __repr__(self):
        return f"Button Released (button={self.button})"


class HatChanged:
    def __init__(self, hat, x, y):
        self.hat = hat
        self.x = x
        self.y = y