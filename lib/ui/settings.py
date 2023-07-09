import json
import socket
from pathlib import Path
from collections import namedtuple

Dimensions = namedtuple("Dimensions", "width height")


class Settings:
    DEFAULT_FONT_SIZE = 18
    DEFAULT_USERNAME = f"officepal-{socket.gethostname()}"
    DEFAULT_WIDTH = 1368
    DEFAULT_HEIGHT = 1000
    APP_DIR = Path.home() / ".lanmessenger"

    def __init__(self):
        self.version = 1
        self.username = Settings.DEFAULT_USERNAME
        self.font_size = Settings.DEFAULT_FONT_SIZE
        self._dimensions = {
            "width": Settings.DEFAULT_WIDTH,
            "height": Settings.DEFAULT_HEIGHT,
        }

        try:
            with open(self.filename, "r") as f:
                settings_dict = json.load(f)
                for key, value in settings_dict.items():
                    setattr(self, key, value)
        except FileNotFoundError:
            pass

    @property
    def filename(self) -> Path:
        return Settings.APP_DIR / "settings.json"

    @property
    def dimensions(self) -> Dimensions:
        return Dimensions(
            width=self._dimensions["width"], height=self._dimensions["height"]
        )

    @dimensions.setter
    def dimensions(self, value: Dimensions):
        self._dimensions["width"] = value.width
        self._dimensions["height"] = value.height

    def serialize(self):
        Settings.APP_DIR.mkdir(exist_ok=True)
        with open(self.filename, "w") as f:
            json.dump(self.__dict__, f)
