import json
import os

FILE = "position_targets.json"


def _load():
    if not os.path.exists(FILE):
        return {}

    with open(FILE, "r") as f:
        return json.load(f)


def _save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)


def save_target(symbol, stop, target):
    data = _load()
    data[symbol] = {"stop": stop, "target": target}
    _save(data)


def get_target(symbol):
    return _load().get(symbol)


def clear_target(symbol):
    data = _load()
    if symbol in data:
        del data[symbol]
        _save(data)
