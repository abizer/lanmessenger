from pathlib import Path
from lib.util import OperatingSystem, get_platfrom
import sys
import os


def load_font():
    platform: OperatingSystem = get_platfrom()

    def _locate_font(font_file_name):
        if platform == OperatingSystem.Windows:
            fonts_dir = [Path(os.environ["WINDIR"]) / "Fonts"]
        elif platform == OperatingSystem.MacOS:
            fonts_dir = [
                Path("/System/Library/Fonts/"),
                Path.home() / "Library" / "Fonts",
            ]
        else:
            fonts_dir = [
                Path("/usr/share/fonts"),
                Path("/usr/local/share/fonts"),
                Path.home() / ".local" / "share" / "fonts",
            ]

        for directory in fonts_dir:
            for font_file in directory.rglob(font_file_name):
                return font_file

        return None  # Font not found

    if platform == OperatingSystem.Windows:
        font_name = "Consola.ttf"
    elif platform == OperatingSystem.MacOS:
        font_name = "SFNSMono.ttf"
    else:
        font_name = "DejaVuSansMono.ttf"
    font_path = _locate_font(font_name)
    return font_path
