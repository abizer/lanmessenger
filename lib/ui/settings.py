from dataclasses import dataclass, asdict, field
import json
import socket
from pathlib import Path
from collections import namedtuple
from uuid import UUID, uuid4

Dimensions = namedtuple("Dimensions", "width height")

APP_DIR: Path = Path.home() / ".lanmessenger"
DEFAULT_USERNAME: str = f"officepal-{socket.gethostname()}"


@dataclass
class Settings:
    uuid: str = field(default_factory=lambda: str(uuid4()))
    font_size: int = 18
    username: str = DEFAULT_USERNAME
    width: int = 1368
    height: int = 1000

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
        return APP_DIR / "settings.json"

    @property
    def dimensions(self) -> Dimensions:
        return Dimensions(width=self.width, height=self.height)

    @dimensions.setter
    def dimensions(self, value: Dimensions):
        self.width = value.width
        self.height = value.height

    def serialize(self):
        APP_DIR.mkdir(exist_ok=True)
        with open(self.filename, "w") as f:
            json.dump(asdict(self), f)


@dataclass
class DevSettings(Settings):
    @property
    def filename(self) -> Path:
        return APP_DIR / f"{self.username}.settings.json"
