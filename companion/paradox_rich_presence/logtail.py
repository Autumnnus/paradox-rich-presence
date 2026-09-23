"""Reads a growing log file like 'tail -f'."""

import sys


class LogTailer:
    """Follows a file like 'tail -f' and starts over when the game rotates debug.log on launch."""

    def __init__(self, path):
        self.path = path
        self.f = None
        self.inode = None
        self.buf = ""

    def _open(self):
        try:
            st = self.path.stat()
        except FileNotFoundError:
            return False
        self.f = open(self.path, encoding="utf-8", errors="replace")
        self.inode = (st.st_ino, st.st_ctime if sys.platform == "win32" else 0)
        self.buf = ""
        return True

    def read_lines(self):
        try:
            st = self.path.stat()
        except FileNotFoundError:
            self.close()
            return []
        ident = (st.st_ino, st.st_ctime if sys.platform == "win32" else 0)
        if self.f is None or ident != self.inode or st.st_size < self.f.tell():
            self.close()
            if not self._open():
                return []
        chunk = self.f.read()
        if not chunk:
            return []
        self.buf += chunk
        *lines, self.buf = self.buf.split("\n")
        return lines

    def close(self):
        if self.f:
            self.f.close()
        self.f = None
