"""D-Bus reads through busctl's JSON output, which copes with the nested
variants many desktop APIs are full of (UPower, MPRIS, DBusMenu, UDisks2)."""
import json

from PySide6.QtCore import QProcess


def unwrap(node):
    """busctl's {"type": …, "data": …} -> plain values."""
    if isinstance(node, dict):
        if set(node) == {"type", "data"}:
            return unwrap(node["data"])
        return {k: unwrap(v) for k, v in node.items()}
    if isinstance(node, list):
        return [unwrap(v) for v in node]
    return node


def busctl(parent, args, done=None, failed=None):
    """Runs busctl in the background; `done` gets one value per JSON line, and
    `failed`, if given, gets busctl's error message when the call fails."""
    proc = QProcess(parent)

    def finished(code, status):
        out = bytes(proc.readAllStandardOutput()).decode(errors="replace")
        err = bytes(proc.readAllStandardError()).decode(errors="replace").strip()
        proc.deleteLater()
        if (code != 0 or status != QProcess.ExitStatus.NormalExit) and failed is not None:
            failed(err or "busctl failed")
            return
        values = []
        for line in out.splitlines():
            try:
                values.append(unwrap(json.loads(line)))
            except ValueError:
                pass
        if done:
            done(values)

    proc.finished.connect(finished)
    proc.start("busctl", args)
    return proc
