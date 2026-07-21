import os
import psutil


def is_locked(name):
    """Read-only check: is a live process currently holding this lock?"""

    lock_path = f"{name}.lock"

    if not os.path.exists(lock_path):
        return False

    with open(lock_path) as f:
        existing_pid = f.read().strip()

    return existing_pid.isdigit() and psutil.pid_exists(int(existing_pid))


def acquire_lock(name):
    """Returns True if the lock was acquired (safe to proceed), False if
    another live process already holds it. Stale locks (holder process no
    longer running) are reclaimed automatically."""

    lock_path = f"{name}.lock"

    if os.path.exists(lock_path):
        with open(lock_path) as f:
            existing_pid = f.read().strip()

        if existing_pid.isdigit():
            pid = int(existing_pid)
            if pid != os.getpid() and psutil.pid_exists(pid):
                return False

    with open(lock_path, "w") as f:
        f.write(str(os.getpid()))

    return True
