import json
import socket
from pathlib import Path

class Settings:
    DEFAULT_FONT_SIZE = 18
    DEFAULT_USERNAME = f"officepal-{socket.gethostname()}"
    APP_DIR = Path.home() / ".lanmessenger"

    def __init__(self):
        self.version = 1
        self.username = Settings.DEFAULT_USERNAME
        self.font_size = Settings.DEFAULT_FONT_SIZE

        try:
            with open(self.filename, 'r') as f:
                settings_dict = json.load(f)
                for key, value in settings_dict.items():
                    setattr(self, key, value)
        except FileNotFoundError:
            pass

    @property
    def filename(self) -> Path:
        return Settings.APP_DIR / "settings.json"

    def serialize(self):
        Settings.APP_DIR.mkdir(exist_ok=True)
        with open(self.filename, 'w') as f:
            json.dump(self.__dict__, f)
