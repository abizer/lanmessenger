from lib.util import OperatingSystem, get_platfrom

platform = get_platfrom()
if platform == OperatingSystem.MacOS:
    from Cocoa import NSApp, NSApplication

def register_app():
    if platform == OperatingSystem.MacOS:
        NSApplication.sharedApplication()

def bring_to_front():
    if platform == OperatingSystem.MacOS:
        NSApp().activateIgnoringOtherApps_(True)