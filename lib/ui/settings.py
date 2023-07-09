from dataclasses import dataclass
import json
import socket
from pathlib import Path
from collections import namedtuple

Dimensions = namedtuple("Dimensions", "width height")


@dataclass
class Settings:
    font_size: int = 18
    username: str = f"officepal-{socket.gethostname()}"
    width: int = 1368
    height: int = 1000
    app_dir: Path = Path.home() / ".lanmessenger"

    def __post_init__(self):
        self.version = 1

        try:
            with open(self.filename, "r") as f:
                settings_dict = json.load(f)
                for key, value in settings_dict.items():
                    setattr(self, key, value)
        except FileNotFoundError:
            pass

    @property
    def filename(self) -> Path:
        return Settings.app_dir / f"{self.username}.settings.json"

    @property
    def dimensions(self) -> Dimensions:
        return Dimensions(width=self.width, height=self.height)

    @dimensions.setter
    def dimensions(self, value: Dimensions):
        self.width = value.width
        self.height = value.height

    def serialize(self):
        Settings.app_dir.mkdir(exist_ok=True)
        with open(self.filename, "w") as f:
            json.dump(self.asdict(), f)
