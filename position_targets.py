import json
import os

FILE = "position_targets.json"
PENDING_EXITS_FILE = "pending_exits.json"


def _load(path=FILE):
    if not os.path.exists(path):
        return {}

    with open(path, "r") as f:
        return json.load(f)


def _save(data, path=FILE):
    with open(path, "w") as f:
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


# Tracks a close order that's been submitted but not yet confirmed filled,
# so monitor_positions doesn't submit a second close order for the same
# position while the first is still in flight, and doesn't log/clear the
# target until the exit is actually confirmed.

def save_pending_exit(symbol, order_id):
    data = _load(PENDING_EXITS_FILE)
    data[symbol] = order_id
    _save(data, PENDING_EXITS_FILE)


def get_pending_exit(symbol):
    return _load(PENDING_EXITS_FILE).get(symbol)


def clear_pending_exit(symbol):
    data = _load(PENDING_EXITS_FILE)
    if symbol in data:
        del data[symbol]
        _save(data, PENDING_EXITS_FILE)
