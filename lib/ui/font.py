from pathlib import Path
import sys
import os

def load_font():
    def _locate_font(font_file_name):
        if sys.platform.startswith('win'):
            # Windows
            fonts_dir = [Path(os.environ['WINDIR']) / 'Fonts']
        elif sys.platform.startswith('darwin'):
            # macOS
            fonts_dir = [Path('/System/Library/Fonts/'), Path.home() / 'Library' / 'Fonts']
        else:
            # Linux
            fonts_dir = [Path('/usr/share/fonts'), Path('/usr/local/share/fonts'), Path.home() / '.local' / 'share' / 'fonts']

        for directory in fonts_dir:
            for font_file in directory.rglob(font_file_name):
                return font_file

        return None  # Font not found

    if sys.platform.startswith('win'):
        font_name = 'Consola.ttf'
    elif sys.platform.startswith('darwin'):
        font_name = 'SFNSMono.ttf'
    else:
        font_name = 'DejaVuSansMono.ttf'
    font_path = _locate_font(font_name)
    return font_path
