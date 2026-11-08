
import os
from datetime import datetime

import pytest

import storage.backup as backup
from config import SaveError


# ==================================================
# FIXTURES
# ==================================================

@pytest.fixture
def backup_paths(tmp_path, monkeypatch):
    main_file = tmp_path / "report.txt"
    backup_file = tmp_path / "report.txt.bak"

    monkeypatch.setattr(
        backup,
        "FILE_NAME",
        str(main_file),
    )

    monkeypatch.setattr(
        backup,
        "BACKUP_NAME",
        str(backup_file),
    )

    return main_file, backup_file


# ==================================================
# NO BACKUP REQUIRED
# ==================================================

def test_backup_file_none_does_nothing(backup_paths):
    main_file, backup_file = backup_paths

    backup.backup_file(None)

    assert not main_file.exists()
    assert not backup_file.exists()


# ==================================================
# VALID BACKUP
# ==================================================

def test_backup_file_creates_backup(backup_paths):
    main_file, backup_file = backup_paths

    main_file.write_text(
        "RATE|104\nENTRY|2026-01-01|500\n",
        encoding="utf-8",
    )

    disk = (
        {"rate": 104},
        [],
        [],
    )

    backup.backup_file(disk)

    assert backup_file.read_text(encoding="utf-8") == (
        "RATE|104\nENTRY|2026-01-01|500\n"
    )

    assert not (backup_file.parent / (backup_file.name + ".tmp")).exists()


def test_backup_file_replaces_existing_backup(backup_paths):
    main_file, backup_file = backup_paths

    main_file.write_text(
        "NEW MAIN CONTENT",
        encoding="utf-8",
    )

    backup_file.write_text(
        "OLD BACKUP CONTENT",
        encoding="utf-8",
    )

    disk = (
        {"rate": 104},
        [],
        [],
    )

    backup.backup_file(disk)

    assert backup_file.read_text(encoding="utf-8") == (
        "NEW MAIN CONTENT"
    )


def test_backup_file_creates_backup_atomically(backup_paths, monkeypatch):
    main_file, backup_file = backup_paths

    main_file.write_text(
        "MAIN CONTENT",
        encoding="utf-8",
    )

    calls = []
    original_replace = backup.os.replace

    def track_replace(source, destination):
        calls.append((source, destination))
        original_replace(source, destination)

    monkeypatch.setattr(
        backup.os,
        "replace",
        track_replace,
    )

    backup.backup_file(
        ({}, [], [])
    )

    assert len(calls) == 1
    assert calls[0][0] == str(backup_file) + ".tmp"
    assert calls[0][1] == str(backup_file)


# ==================================================
# INVALID MAIN FILE
# ==================================================

def test_backup_file_preserves_invalid_main_file(
    backup_paths,
    monkeypatch,
):
    main_file, backup_file = backup_paths

    main_file.write_text(
        "INVALID CONTENT",
        encoding="utf-8",
    )

    backup_file.write_text(
        "KNOWN GOOD BACKUP",
        encoding="utf-8",
    )

    class FixedDateTime:
        @staticmethod
        def now():
            return datetime(2026, 2, 1, 12, 30, 45)

    monkeypatch.setattr(
        backup,
        "datetime",
        FixedDateTime,
    )

    disk = (
        {},
        ["invalid record"],
        [],
    )

    backup.backup_file(disk)

    unverified = main_file.parent / (
        "report.txt.unverified-20260201_123045"
    )

    assert unverified.exists()
    assert unverified.read_text(encoding="utf-8") == "INVALID CONTENT"

    assert backup_file.read_text(encoding="utf-8") == (
        "KNOWN GOOD BACKUP"
    )


def test_backup_file_preserves_accounting_problems(
    backup_paths,
    monkeypatch,
):
    main_file, backup_file = backup_paths

    main_file.write_text(
        "ACCOUNTING PROBLEM",
        encoding="utf-8",
    )

    backup_file.write_text(
        "KNOWN GOOD BACKUP",
        encoding="utf-8",
    )

    class FixedDateTime:
        @staticmethod
        def now():
            return datetime(2026, 2, 1, 12, 30, 45)

    monkeypatch.setattr(
        backup,
        "datetime",
        FixedDateTime,
    )

    disk = (
        {},
        [],
        ["accounting problem"],
    )

    backup.backup_file(disk)

    unverified = main_file.parent / (
        "report.txt.unverified-20260201_123045"
    )

    assert unverified.exists()
    assert unverified.read_text(encoding="utf-8") == (
        "ACCOUNTING PROBLEM"
    )

    assert backup_file.read_text(encoding="utf-8") == (
        "KNOWN GOOD BACKUP"
    )


# ==================================================
# ERROR HANDLING
# ==================================================

def test_backup_file_unverified_copy_failure(
    backup_paths,
    monkeypatch,
):
    main_file, backup_file = backup_paths

    main_file.write_text(
        "INVALID CONTENT",
        encoding="utf-8",
    )

    def fail_copy(source, destination):
        raise OSError("copy failed")

    monkeypatch.setattr(
        backup.shutil,
        "copy2",
        fail_copy,
    )

    disk = (
        {},
        ["invalid record"],
        [],
    )

    with pytest.raises(
        SaveError,
        match="Could not preserve the invalid main file",
    ):
        backup.backup_file(disk)


def test_backup_file_write_failure(backup_paths, monkeypatch):
    main_file, backup_file = backup_paths

    main_file.write_text(
        "MAIN CONTENT",
        encoding="utf-8",
    )

    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr(
        backup.os,
        "replace",
        fail_replace,
    )

    disk = (
        {},
        [],
        [],
    )

    with pytest.raises(
        SaveError,
        match="Could not create a safe backup",
    ):
        backup.backup_file(disk)

    assert not os.path.exists(str(backup_file) + ".tmp")


def test_backup_file_preserves_old_backup_on_failure(
    backup_paths,
    monkeypatch,
):
    main_file, backup_file = backup_paths

    main_file.write_text(
        "NEW MAIN CONTENT",
        encoding="utf-8",
    )

    backup_file.write_text(
        "OLD BACKUP CONTENT",
        encoding="utf-8",
    )

    def fail_replace(source, destination):
        raise OSError("replace failed")

    monkeypatch.setattr(
        backup.os,
        "replace",
        fail_replace,
    )

    with pytest.raises(SaveError):
        backup.backup_file(
            ({}, [], [])
        )

    assert backup_file.read_text(encoding="utf-8") == (
        "OLD BACKUP CONTENT"
    )
