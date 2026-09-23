"""Discord'un yerel RPC (IPC) protokolu icin kucuk, bagimliliksiz bir istemci."""

import json
import logging
import os
import socket
import struct
import sys
import uuid

log = logging.getLogger(__name__)


def _unix_temp_dirs():
    dirs = []
    for var in ("XDG_RUNTIME_DIR", "TMPDIR", "TMP", "TEMP"):
        if os.environ.get(var):
            dirs.append(os.environ[var])
    if sys.platform == "darwin":
        # launchd ile baslatilan ajanlarda TMPDIR tanimli olmayabilir; Discord soketi
        # kullanicinin Darwin gecici klasorundedir.
        try:
            dirs.append(os.confstr(65537))  # _CS_DARWIN_USER_TEMP_DIR
        except (ValueError, OSError):
            pass
    dirs.append("/tmp")
    return [d for i, d in enumerate(dirs) if d and d not in dirs[:i]]


class DiscordIPC:
    OP_HANDSHAKE, OP_FRAME, OP_CLOSE = 0, 1, 2

    def __init__(self, client_id):
        self.client_id = client_id
        self.sock = None
        self.pipe = None

    @staticmethod
    def _candidates():
        if sys.platform == "win32":
            return [r"\\?\pipe\discord-ipc-%d" % i for i in range(10)]
        dirs = []
        for base in _unix_temp_dirs():
            dirs += [base, os.path.join(base, "app/com.discordapp.Discord"),
                     os.path.join(base, "snap.discord")]
        return [os.path.join(d, "discord-ipc-%d" % i) for d in dirs for i in range(10)]

    def connect(self):
        for path in self._candidates():
            try:
                if sys.platform == "win32":
                    self.pipe = open(path, "r+b", buffering=0)
                else:
                    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    s.settimeout(5)
                    try:
                        s.connect(path)
                    except OSError:
                        s.close()
                        raise
                    self.sock = s
            except OSError:
                continue
            self._send(self.OP_HANDSHAKE, {"v": 1, "client_id": self.client_id})
            op, data = self._recv()
            if op == self.OP_FRAME and data.get("evt") == "READY":
                user = data.get("data", {}).get("user", {})
                log.info("Discord'a baglanildi (%s)", user.get("username", "?"))
                return True
            self.close()
            raise ConnectionError("Discord el sikismayi reddetti: %s" % data)
        return False

    def _send(self, op, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        frame = struct.pack("<II", op, len(body)) + body
        if self.pipe:
            self.pipe.write(frame)
        else:
            self.sock.sendall(frame)

    def _read_exact(self, n):
        data = b""
        while len(data) < n:
            chunk = self.pipe.read(n - len(data)) if self.pipe else self.sock.recv(n - len(data))
            if not chunk:
                raise ConnectionError("Discord baglantisi kapandi")
            data += chunk
        return data

    def _recv(self):
        op, length = struct.unpack("<II", self._read_exact(8))
        return op, json.loads(self._read_exact(length).decode("utf-8"))

    def set_activity(self, activity):
        self._send(self.OP_FRAME, {
            "cmd": "SET_ACTIVITY",
            "args": {"pid": os.getpid(), "activity": activity},
            "nonce": str(uuid.uuid4()),
        })
        op, data = self._recv()
        if data.get("evt") == "ERROR":
            raise ValueError("Discord etkinligi reddetti: %s" % data.get("data"))

    def close(self):
        for h in (self.sock, self.pipe):
            try:
                if h:
                    h.close()
            except OSError:
                pass
        self.sock = self.pipe = None

    @property
    def connected(self):
        return bool(self.sock or self.pipe)
