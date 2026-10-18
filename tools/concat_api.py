"""Cliente mínimo da API JSON-RPC do Concat (127.0.0.1:7420)."""
import json
import os
import socket

# O token da API do Concat (Configurações › API), na raiz do repositório e fora do Git.
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".concat-token")


class Concat:
    def __init__(self, path, host="127.0.0.1", port=7420, token=None):
        token = token or os.environ.get("CONCAT_TOKEN") or open(TOKEN_FILE).read().strip()
        self.path = path
        self.sock = socket.create_connection((host, port), timeout=300)
        self.file = self.sock.makefile("rw", encoding="utf-8", newline="\n")
        self.next_id = 0
        self.call("auth", token=token)

    def call(self, method, **params):
        self.next_id += 1
        self.file.write(json.dumps({"jsonrpc": "2.0", "id": self.next_id, "method": method, "params": params}) + "\n")
        self.file.flush()
        while True:
            reply = json.loads(self.file.readline())
            if reply.get("id") == self.next_id:
                break
        if "error" in reply:
            raise RuntimeError(f"{method}: {reply['error']['message']}")
        return reply["result"]

    def view(self):
        return self.call("project.get", path=self.path)

    def edit(self, command):
        return self.call("edit.apply", path=self.path, command=command)

    def batch(self, commands):
        return self.edit({"op": "batch", "commands": commands})


def timeline(view):
    project = view["project"]
    return next(t for t in project["timelines"] if t["id"] == project["activeTimelineId"])


def fps_de(path):
    """Quadros por segundo da timeline do projeto em `path` (lido do concat.json)."""
    p = json.load(open(os.path.join(path, "concat.json")))
    v = (p.get("timelines") or [{}])[0].get("video") or p.get("video") or {}
    return v.get("rateNum", 24) / v.get("rateDen", 1)
