"""OS-specific helpers: folders, process list and Windows integration.

Standard library only; Windows APIs are reached through ctypes/winreg.
"""

import os
import subprocess
import sys
from pathlib import Path

from . import APP_ID, APP_NAME

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


# --------------------------------------------------------------------------- folders

def documents_dir():
    """Parent of the Paradox Interactive user folder.

    On Windows the Documents folder may be redirected (e.g. to OneDrive), so the
    known-folder API is used. On Linux Paradox uses ~/.local/share.
    """
    if IS_WINDOWS:
        path = _windows_known_folder("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")  # FOLDERID_Documents
        if path:
            return Path(path)
        return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Documents"
    if IS_MAC:
        return Path.home() / "Documents"
    return Path.home() / ".local" / "share"


def data_dir():
    """Folder for the config and log files (created if missing)."""
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA", str(Path.home())))
    elif IS_MAC:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
    path = base / APP_ID
    path.mkdir(parents=True, exist_ok=True)
    return path


def _windows_known_folder(guid):
    import ctypes
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [("Data1", wintypes.DWORD), ("Data2", wintypes.WORD),
                    ("Data3", wintypes.WORD), ("Data4", ctypes.c_ubyte * 8)]

    g = GUID()
    if ctypes.oledll.ole32.CLSIDFromString(guid, ctypes.byref(g)) != 0:
        return None
    out = ctypes.c_wchar_p()
    try:
        ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(g), 0, None, ctypes.byref(out))
        return out.value
    except OSError:
        return None
    finally:
        if out:
            ctypes.windll.ole32.CoTaskMemFree(out)


# --------------------------------------------------------------------------- processes

def running_process_names():
    """Lowercase names of the running processes."""
    try:
        if IS_WINDOWS:
            out = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True,
                creationflags=0x08000000,  # CREATE_NO_WINDOW: no console flash from the windowless app
            ).stdout
            return {line.split(",")[0].strip('"').lower() for line in out.splitlines() if line}
        out = subprocess.run(["ps", "-A", "-o", "comm="], capture_output=True, text=True).stdout
        return {os.path.basename(line.strip()).lower() for line in out.splitlines()}
    except OSError:
        return set()


# --------------------------------------------------------------------------- Windows

class WindowsInstance:
    """Single-instance lock and stop signal (named mutex + event)."""

    MUTEX_NAME = "Local\\%s.Instance" % APP_ID
    EVENT_NAME = "Local\\%s.Stop" % APP_ID

    def __init__(self):
        import ctypes
        self._k32 = ctypes.windll.kernel32
        self._mutex = self._k32.CreateMutexW(None, False, self.MUTEX_NAME)
        self.already_running = self._k32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
        self._event = self._k32.CreateEventW(None, True, False, self.EVENT_NAME)

    def stop_requested(self):
        return self._k32.WaitForSingleObject(self._event, 0) == 0  # WAIT_OBJECT_0

    def request_stop(self):
        self._k32.SetEvent(self._event)


def message_box(text, yes_no=False):
    """Windows message box; with yes_no, returns True when Yes is clicked."""
    import ctypes
    MB_YESNO, MB_ICONINFO, MB_ICONQUESTION, IDYES = 0x4, 0x40, 0x20, 6
    style = (MB_YESNO | MB_ICONQUESTION) if yes_no else MB_ICONINFO
    return ctypes.windll.user32.MessageBoxW(None, text, APP_NAME, style) == IDYES


_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_enabled():
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_ID)
            return True
    except OSError:
        return False


def set_autostart(enabled):
    """Start at sign-in, per user (no administrator rights needed)."""
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, APP_ID, 0, winreg.REG_SZ, '"%s"' % sys.executable)
        else:
            try:
                winreg.DeleteValue(key, APP_ID)
            except OSError:
                pass
