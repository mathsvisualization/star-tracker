
from decimal import Decimal

import pytest

import storage.file_manager as fm
from config import SaveError


# ==================================================
# SAMPLE DATA
# ==================================================

@pytest.fixture
def sample_data():
    return {
        "rate": Decimal("104"),
        "earnings": {
            "2026-01-01": 1000,
            "2026-01-10": 500,
        },
        "withdrawals": [
            {
                "date": "2026-01-25",
                "stars": 200,
                "rate": Decimal("104"),
            },
            {
                "date": "2026-02-01",
                "stars": 300,
                "rate": Decimal("105"),
            },
        ],
        "locked": False,
        "issues": [],
    }


# ==================================================
# FILE READING
# ==================================================

def test_read_records(tmp_path):
    path = tmp_path / "report.txt"

    path.write_text(
        "RATE|104\n"
        "ENTRY|2026-01-01|500\n",
        encoding="utf-8",
    )

    data, issues = fm.read_records(path)

    assert issues == []
    assert data["rate"] == Decimal("104")
    assert data["earnings"] == {
        "2026-01-01": 500,
    }


def test_read_records_invalid_record(tmp_path):
    path = tmp_path / "report.txt"

    path.write_text(
        "UNKNOWN|value\n",
        encoding="utf-8",
    )

    data, issues = fm.read_records(path)

    assert len(issues) == 1
    assert "unknown record tag" in issues[0]


def test_read_records_missing_file(tmp_path):
    path = tmp_path / "missing.txt"

    with pytest.raises(FileNotFoundError):
        fm.read_records(path)


# ==================================================
# DISK FILE INSPECTION
# ==================================================

def test_inspect_disk_file_missing(monkeypatch):
    monkeypatch.setattr(
        fm.os.path,
        "exists",
        lambda path: False,
    )

    assert fm.inspect_disk_file() is None


def test_inspect_disk_file_valid(monkeypatch):
    data = {
        "rate": Decimal("104"),
        "earnings": {"2026-01-01": 500},
        "withdrawals": [],
        "locked": False,
        "issues": [],
    }

    monkeypatch.setattr(
        fm.os.path,
        "exists",
        lambda path: True,
    )

    monkeypatch.setattr(
        fm,
        "read_records",
        lambda path: (data, []),
    )

    monkeypatch.setattr(
        fm,
        "accounting_problems",
        lambda data: [],
    )

    result = fm.inspect_disk_file()

    assert result == (data, [], [])


def test_inspect_disk_file_with_syntax_issues(monkeypatch):
    data = {
        "rate": Decimal("104"),
        "earnings": {},
        "withdrawals": [],
        "locked": False,
        "issues": [],
    }

    issues = ["line 1: invalid number"]

    monkeypatch.setattr(
        fm.os.path,
        "exists",
        lambda path: True,
    )

    monkeypatch.setattr(
        fm,
        "read_records",
        lambda path: (data, issues),
    )

    def should_not_run(data):
        pytest.fail("Accounting validation should not run")

    monkeypatch.setattr(
        fm,
        "accounting_problems",
        should_not_run,
    )

    result = fm.inspect_disk_file()

    assert result == (data, issues, [])


def test_inspect_disk_file_accounting_problems(monkeypatch):
    data = {
        "rate": Decimal("104"),
        "earnings": {},
        "withdrawals": [],
        "locked": False,
        "issues": [],
    }

    problems = ["accounting problem"]

    monkeypatch.setattr(
        fm.os.path,
        "exists",
        lambda path: True,
    )

    monkeypatch.setattr(
        fm,
        "read_records",
        lambda path: (data, []),
    )

    monkeypatch.setattr(
        fm,
        "accounting_problems",
        lambda data: problems,
    )

    result = fm.inspect_disk_file()

    assert result == (data, [], problems)


def test_inspect_disk_file_read_error(monkeypatch):
    monkeypatch.setattr(
        fm.os.path,
        "exists",
        lambda path: True,
    )

    def fail_read(path):
        raise OSError("disk read failed")

    monkeypatch.setattr(
        fm,
        "read_records",
        fail_read,
    )

    with pytest.raises(OSError, match="disk read failed"):
        fm.inspect_disk_file()


# ==================================================
# ATOMIC WRITING
# ==================================================

def test_write_atomic_creates_file(tmp_path):
    path = tmp_path / "report.txt"

    fm.write_atomic(
        str(path),
        "Hello World",
    )

    assert path.read_text(encoding="utf-8") == "Hello World"
    assert not (tmp_path / "report.txt.tmp").exists()


def test_write_atomic_replaces_existing_file(tmp_path):
    path = tmp_path / "report.txt"

    path.write_text(
        "Old content",
        encoding="utf-8",
    )

    fm.write_atomic(
        str(path),
        "New content",
    )

    assert path.read_text(encoding="utf-8") == "New content"


def test_write_atomic_removes_temp_file_on_failure(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "report.txt"
    tmp_path_file = tmp_path / "report.txt.tmp"

    path.write_text(
        "Original content",
        encoding="utf-8",
    )

    def fail_replace(src, dst):
        raise OSError("replace failed")

    monkeypatch.setattr(
        fm.os,
        "replace",
        fail_replace,
    )

    with pytest.raises(OSError, match="replace failed"):
        fm.write_atomic(
            str(path),
            "New content",
        )

    assert path.read_text(encoding="utf-8") == "Original content"
    assert not tmp_path_file.exists()


def test_write_atomic_preserves_temp_cleanup_if_remove_fails(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "report.txt"

    def fail_replace(src, dst):
        raise OSError("replace failed")

    def fail_remove(path):
        raise OSError("remove failed")

    monkeypatch.setattr(
        fm.os,
        "replace",
        fail_replace,
    )

    monkeypatch.setattr(
        fm.os,
        "remove",
        fail_remove,
    )

    with pytest.raises(OSError, match="replace failed"):
        fm.write_atomic(
            str(path),
            "New content",
        )


# ==================================================
# RECORD SERIALIZATION
# ==================================================

def test_serialize_records(sample_data):
    records = fm.serialize_records(sample_data)

    assert records[0] == "RATE|104"

    assert records[1:3] == [
        "ENTRY|2026-01-01|1000",
        "ENTRY|2026-01-10|500",
    ]

    assert records[3:] == [
        "WITHDRAW|2026-01-25|200|104",
        "WITHDRAW|2026-02-01|300|105",
    ]


def test_serialize_records_sorts_earnings():
    data = {
        "rate": Decimal("104"),
        "earnings": {
            "2026-01-10": 500,
            "2026-01-01": 1000,
        },
        "withdrawals": [],
    }

    records = fm.serialize_records(data)

    assert records == [
        "RATE|104",
        "ENTRY|2026-01-01|1000",
        "ENTRY|2026-01-10|500",
    ]


def test_serialize_records_without_withdrawals():
    data = {
        "rate": Decimal("104"),
        "earnings": {
            "2026-01-01": 500,
        },
        "withdrawals": [],
    }

    records = fm.serialize_records(data)

    assert records == [
        "RATE|104",
        "ENTRY|2026-01-01|500",
    ]


# ==================================================
# ROUND-TRIP VALIDATION
# ==================================================

def test_validate_serialized_data_valid(sample_data):
    records = fm.serialize_records(sample_data)

    fm.validate_serialized_data(
        sample_data,
        records,
    )


def test_validate_serialized_data_invalid_records(sample_data):
    records = [
        "UNKNOWN|value",
    ]

    with pytest.raises(SaveError, match="data failed validation"):
        fm.validate_serialized_data(
            sample_data,
            records,
        )


def test_validate_serialized_data_rate_mismatch(sample_data):
    records = fm.serialize_records(sample_data)

    sample_data["rate"] = Decimal("105")

    with pytest.raises(SaveError, match="records do not match"):
        fm.validate_serialized_data(
            sample_data,
            records,
        )


def test_validate_serialized_data_earnings_mismatch(sample_data):
    records = fm.serialize_records(sample_data)

    sample_data["earnings"]["2026-01-15"] = 100

    with pytest.raises(SaveError, match="records do not match"):
        fm.validate_serialized_data(
            sample_data,
            records,
        )


def test_validate_serialized_data_withdrawals_mismatch(sample_data):
    records = fm.serialize_records(sample_data)

    sample_data["withdrawals"].append({
        "date": "2026-02-05",
        "stars": 100,
        "rate": Decimal("104"),
    })

    with pytest.raises(SaveError, match="records do not match"):
        fm.validate_serialized_data(
            sample_data,
            records,
        )


# ==================================================
# SAFE SAVING
# ==================================================

def test_save_data_rejects_locked_data(sample_data):
    sample_data["locked"] = True

    with pytest.raises(SaveError, match="editing is locked"):
        fm.save_data(sample_data)


def test_save_data_rejects_invalid_serialized_data(
    sample_data,
    monkeypatch,
):
    def fail_validation(data, records):
        raise SaveError("validation failed")

    monkeypatch.setattr(
        fm,
        "validate_serialized_data",
        fail_validation,
    )

    with pytest.raises(SaveError, match="validation failed"):
        fm.save_data(sample_data)


def test_save_data_handles_disk_read_error(
    sample_data,
    monkeypatch,
):
    def fail_inspection():
        raise OSError("disk unavailable")

    monkeypatch.setattr(
        fm,
        "inspect_disk_file",
        fail_inspection,
    )

    with pytest.raises(SaveError, match="could not read the current file"):
        fm.save_data(sample_data)


def test_save_data_prevents_new_accounting_shortfall(
    sample_data,
    monkeypatch,
):
    old_data = {
        "rate": Decimal("104"),
        "earnings": {},
        "withdrawals": [],
        "locked": False,
        "issues": [],
    }

    sample_data["earnings"] = {
        "2026-01-01": 500,
    }

    sample_data["withdrawals"] = [
        {
            "date": "2026-01-20",
            "stars": 1000,
            "rate": Decimal("104"),
        }
    ]

    monkeypatch.setattr(
        fm,
        "inspect_disk_file",
        lambda: (old_data, [], []),
    )

    def should_not_backup(disk):
        pytest.fail("Backup should not run")

    monkeypatch.setattr(
        fm,
        "backup_file",
        should_not_backup,
    )

    with pytest.raises(SaveError, match="accounting check failed"):
        fm.save_data(sample_data)


def test_save_data_skips_accounting_guard_when_disk_has_syntax_issues(
    sample_data,
    monkeypatch,
):
    old_data = {
        "rate": Decimal("104"),
        "earnings": {},
        "withdrawals": [],
        "locked": False,
        "issues": [],
    }

    monkeypatch.setattr(
        fm,
        "inspect_disk_file",
        lambda: (
            old_data,
            ["line 1: invalid number"],
            [],
        ),
    )

    monkeypatch.setattr(
        fm,
        "backup_file",
        lambda disk: None,
    )

    saved = {}

    monkeypatch.setattr(
        fm,
        "write_atomic",
        lambda path, text: saved.update({
            "path": path,
            "text": text,
        }),
    )

    monkeypatch.setattr(
        fm,
        "build_report",
        lambda data: "TEST REPORT",
    )

    fm.save_data(sample_data)

    assert saved["path"] == fm.FILE_NAME
    assert "TEST REPORT" in saved["text"]


def test_save_data_calls_backup(
    sample_data,
    monkeypatch,
):
    disk = (
        {
            "rate": Decimal("104"),
            "earnings": {},
            "withdrawals": [],
        },
        [],
        [],
    )

    calls = []

    monkeypatch.setattr(
        fm,
        "inspect_disk_file",
        lambda: disk,
    )

    monkeypatch.setattr(
        fm,
        "backup_file",
        lambda value: calls.append(value),
    )

    monkeypatch.setattr(
        fm,
        "write_atomic",
        lambda path, text: None,
    )

    monkeypatch.setattr(
        fm,
        "build_report",
        lambda data: "TEST REPORT",
    )

    fm.save_data(sample_data)

    assert calls == [disk]


def test_save_data_writes_complete_report(
    sample_data,
    monkeypatch,
):
    saved = {}

    monkeypatch.setattr(
        fm,
        "inspect_disk_file",
        lambda: None,
    )

    monkeypatch.setattr(
        fm,
        "backup_file",
        lambda disk: None,
    )

    monkeypatch.setattr(
        fm,
        "build_report",
        lambda data: "GENERATED REPORT",
    )

    def fake_write(path, text):
        saved["path"] = path
        saved["text"] = text

    monkeypatch.setattr(
        fm,
        "write_atomic",
        fake_write,
    )

    fm.save_data(sample_data)

    assert saved["path"] == fm.FILE_NAME
    assert saved["text"].startswith("RATE|104\n")
    assert "\n\nGENERATED REPORT" in saved["text"]


def test_save_data_handles_write_error(
    sample_data,
    monkeypatch,
):
    monkeypatch.setattr(
        fm,
        "inspect_disk_file",
        lambda: None,
    )

    monkeypatch.setattr(
        fm,
        "backup_file",
        lambda disk: None,
    )

    monkeypatch.setattr(
        fm,
        "build_report",
        lambda data: "TEST REPORT",
    )

    def fail_write(path, text):
        raise OSError("disk full")

    monkeypatch.setattr(
        fm,
        "write_atomic",
        fail_write,
    )

    with pytest.raises(SaveError, match="could not write the main report"):
        fm.save_data(sample_data)
