class ControllerConnected:
    def __init__(self, name, instance_id):
        self.name = name
        self.instance_id = instance_id


class ControllerDisconnected:
    def __init__(self,name,instance_id):
        self.name=name
        self.instance_id=instance_id


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