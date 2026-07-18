"""Tests for experiment status rules and local photo storage."""

import pytest

from app.lab.experiments import can_transition
from app.storage.local import LocalStorage


def test_status_transitions():
    assert can_transition("planned", "running")
    assert can_transition("planned", "done")
    assert can_transition("running", "done")
    assert can_transition("planned", "planned")  # no-op OK
    assert not can_transition("done", "running")
    assert not can_transition("running", "planned")
    assert not can_transition("planned", "bogus")


def test_local_storage_roundtrip(tmp_path):
    store = LocalStorage(root=str(tmp_path))
    key = store.save(7, "image/png", b"\x89PNG_fake")
    assert key.startswith("attachments/7/")
    assert key.endswith(".png")
    assert store.load(key) == b"\x89PNG_fake"
    store.delete(key)
    with pytest.raises(FileNotFoundError):
        store.load(key)


def test_local_storage_rejects_bad_type(tmp_path):
    store = LocalStorage(root=str(tmp_path))
    with pytest.raises(ValueError, match="Unsupported"):
        store.save(1, "application/pdf", b"%PDF")


def test_local_storage_rejects_path_traversal(tmp_path):
    store = LocalStorage(root=str(tmp_path))
    with pytest.raises(ValueError, match="Invalid"):
        store.path_for("../etc/passwd")
