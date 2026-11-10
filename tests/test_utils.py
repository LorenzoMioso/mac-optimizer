"""
Test per le funzioni di utilità in mac_optimizer.utils.
"""

import os
import tempfile
from mac_optimizer.utils import (
    format_bytes,
    run_cmd,
    fast_get_path_size,
    safe_remove_directory_contents,
    get_disk_free_info,
)


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(-100) == "0 B"
    assert format_bytes(500) == "500 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"
    assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"
    assert format_bytes(1024 * 1024 * 1024 * 1024) == "1.0 TB"
    assert format_bytes(int(1.5 * 1024 * 1024 * 1024)) == "1.5 GB"


def test_run_cmd_success():
    code, out, err = run_cmd(["echo", "hello mac-optimizer"])
    assert code == 0
    assert "hello mac-optimizer" in out
    assert err == ""


def test_run_cmd_failure():
    code, out, err = run_cmd(["ls", "/percorso_inesistente_12345"])
    assert code != 0
    assert err != ""


def test_run_cmd_timeout():
    code, out, err = run_cmd(["sleep", "2"], timeout=0.1)
    assert code == -1
    assert "Timeout" in err


def test_fast_get_path_size(tmp_path):
    assert fast_get_path_size(str(tmp_path / "inesistente")) == 0

    f = tmp_path / "test.txt"
    f.write_text("a" * 1000)
    assert fast_get_path_size(str(f)) == 1000

    sub = tmp_path / "subdir"
    sub.mkdir()
    f2 = sub / "test2.txt"
    f2.write_text("b" * 2000)
    assert fast_get_path_size(str(tmp_path)) >= 3000


def test_safe_remove_directory_contents(tmp_path):
    parent = tmp_path / "target_dir"
    parent.mkdir()
    (parent / "file1.txt").write_text("data 1")
    (parent / "file2.txt").write_text("data 2")
    sub = parent / "nested"
    sub.mkdir()
    (sub / "file3.txt").write_text("data 3")

    assert os.path.exists(parent)
    removed, errors = safe_remove_directory_contents(str(parent))
    assert removed == 3
    assert errors == 0
    assert os.path.exists(parent)
    assert len(os.listdir(parent)) == 0


def test_get_disk_free_info():
    info = get_disk_free_info()
    assert "total" in info
    assert "free" in info
    assert "percent" in info
    assert "GB" in info["total"]
    assert "GB" in info["free"]
