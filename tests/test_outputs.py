"""Acceptance tests for hidden-channel fingerprint reconciliation."""

import copy
import json
import os
import subprocess
import sys

import pytest


ENTRY = os.environ.get("RESONANCE_PROBE_ENTRY", "/app/resonance_probe_reconcile.py")
PROFILES = [{'probe_id': 'RIG-A', 'fingerprint': [182.0, 0.84, 17.5]},
 {'probe_id': 'RIG-B', 'fingerprint': [236.0, 1.27, 31.0]},
 {'probe_id': 'RIG-C', 'fingerprint': [311.0, 0.63, 44.5]},
 {'probe_id': 'RIG-D', 'fingerprint': [407.0, 1.48, 58.0]},
 {'probe_id': 'RIG-E', 'fingerprint': [193.847, 0.9116, 18.6545]},
 {'probe_id': 'RIG-F', 'fingerprint': [266.714, 1.4691, 35.064]},
 {'probe_id': 'RIG-G', 'fingerprint': [371.696, 0.80385, 53.2285]},
 {'probe_id': 'RIG-H', 'fingerprint': [512.888, 1.9328, 73.148]},
 {'probe_id': 'RIG-I', 'fingerprint': [241.235, 1.198, 23.2725]},
 {'probe_id': 'RIG-J', 'fingerprint': [328.142, 1.8673, 43.192]}]
READINGS = [{'slot': 'CH-3',
  'drive_hz': 182.0,
  'amplitude_mm': 0.84,
  'phase_deg': 17.5,
  'temperature_c': 22.0,
  'settle_ms': 100.0},
 {'slot': 'CH-10',
  'drive_hz': 236.0,
  'amplitude_mm': 1.27,
  'phase_deg': 31.0,
  'temperature_c': 22.0,
  'settle_ms': 100.0},
 {'slot': 'CH-6',
  'drive_hz': 311.0,
  'amplitude_mm': 0.63,
  'phase_deg': 44.5,
  'temperature_c': 22.0,
  'settle_ms': 100.0},
 {'slot': 'CH-13',
  'drive_hz': 407.0,
  'amplitude_mm': 1.48,
  'phase_deg': 58.0,
  'temperature_c': 22.0,
  'settle_ms': 100.0},
 {'slot': 'CH-9',
  'drive_hz': 193.847,
  'amplitude_mm': 0.9116,
  'phase_deg': 18.6545,
  'temperature_c': 22.0,
  'settle_ms': 100.0},
 {'slot': 'CH-5',
  'drive_hz': 266.714,
  'amplitude_mm': 1.4691,
  'phase_deg': 35.064,
  'temperature_c': 22.0,
  'settle_ms': 100.0},
 {'slot': 'CH-12',
  'drive_hz': 371.696,
  'amplitude_mm': 0.80385,
  'phase_deg': 53.2285,
  'temperature_c': 22.0,
  'settle_ms': 100.0},
 {'slot': 'CH-8',
  'drive_hz': 512.888,
  'amplitude_mm': 1.9328,
  'phase_deg': 73.148,
  'temperature_c': 22.0,
  'settle_ms': 100.0},
 {'slot': 'CH-4',
  'drive_hz': 241.235,
  'amplitude_mm': 1.198,
  'phase_deg': 23.2725,
  'temperature_c': 22.0,
  'settle_ms': 100.0},
 {'slot': 'CH-11',
  'drive_hz': 328.142,
  'amplitude_mm': 1.8673,
  'phase_deg': 43.192,
  'temperature_c': 22.0,
  'settle_ms': 100.0}]
EXPECTED_ROWS = [{'slot': 'CH-10', 'probe_id': 'RIG-B', 'residual': 0.0},
 {'slot': 'CH-11', 'probe_id': 'RIG-J', 'residual': 0.0},
 {'slot': 'CH-12', 'probe_id': 'RIG-G', 'residual': 0.0},
 {'slot': 'CH-13', 'probe_id': 'RIG-D', 'residual': 0.0},
 {'slot': 'CH-3', 'probe_id': 'RIG-A', 'residual': 0.0},
 {'slot': 'CH-4', 'probe_id': 'RIG-I', 'residual': 0.0},
 {'slot': 'CH-5', 'probe_id': 'RIG-F', 'residual': 0.0},
 {'slot': 'CH-6', 'probe_id': 'RIG-C', 'residual': 0.0},
 {'slot': 'CH-8', 'probe_id': 'RIG-H', 'residual': 0.0},
 {'slot': 'CH-9', 'probe_id': 'RIG-E', 'residual': 0.0}]
OUTPUT_KEYS = ['rig_id', 'status', 'probe_assignments', 'total_residual', 'accepted', 'diagnostic']
LEDGER_KEYS = ['rig_id', 'input_sha256', 'result_sha256', 'total_residual']


def base_payload():
    return {
        "rig_id": "RIG-STD-7",
        "limits": {"max_slots": 12, "residual_ceiling": 0.02},
        "profiles": copy.deepcopy(PROFILES),
        "readings": copy.deepcopy(READINGS),
    }


def invoke(tmp_path, payload=None, ledger=None, raw=None, output_name="result.json"):
    source = tmp_path / "readings.json"
    target = tmp_path / output_name
    if raw is None:
        raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    source.write_bytes(raw.encode("utf-8"))
    command = [sys.executable, ENTRY, str(source), str(target)]
    if ledger is not None:
        command.append(str(ledger))
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30)
    return completed, source, target


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_success_writes_aligned_output_quietly(tmp_path):
    """题面：「台架成功归档时 stdout 与 stderr 均为空，结果文件本身承担完成信号。」"""
    result, _, output = invoke(tmp_path, base_payload())
    assert result.returncode == 0
    assert result.stdout == "" and result.stderr == ""
    assert output.is_file()


def test_global_assignment_is_minimum_residual(tmp_path):
    """题面：「十条采集记录须共同组成总指纹误差最低的非重复探头对应。」"""
    result, _, output = invoke(tmp_path, base_payload())
    document = read(output)
    assert result.returncode == 0
    assert [(row["slot"], row["probe_id"]) for row in document["probe_assignments"]] == [(row["slot"], row["probe_id"]) for row in EXPECTED_ROWS]
    assert [row["residual"] for row in document["probe_assignments"]] == pytest.approx([row["residual"] for row in EXPECTED_ROWS], abs=1e-12)


def test_assignment_rows_have_exact_fields(tmp_path):
    """题面：「probe_assignments 内的一行由 slot、probe_id、residual 三部分组成。」"""
    result, _, output = invoke(tmp_path, base_payload())
    document = read(output)
    assert result.returncode == 0
    assert all(set(row) == {"slot", "probe_id", "residual"} for row in document["probe_assignments"])


def test_output_has_exact_top_level_keys(tmp_path):
    """题面：「报告最外层出现 rig_id、status、probe_assignments、total_residual、accepted、diagnostic。」"""
    result, _, output = invoke(tmp_path, base_payload())
    document = read(output)
    assert result.returncode == 0
    assert list(document) == OUTPUT_KEYS


def test_output_is_compact_utf8_with_single_lf(tmp_path):
    """题面：「JSON 编码紧凑，UTF-8 文本以一个换行符收尾。」"""
    result, _, output = invoke(tmp_path, base_payload())
    raw = output.read_bytes()
    assert result.returncode == 0
    assert raw.endswith(b"\n") and not raw.endswith(b"\n\n")
    assert b": " not in raw and b", " not in raw


def test_total_residual_matches_assignment(tmp_path):
    """题面：「total_residual 对全部行 residual 求算术和。」"""
    result, _, output = invoke(tmp_path, base_payload())
    document = read(output)
    total = sum(row["residual"] for row in document["probe_assignments"])
    assert result.returncode == 0
    assert document["total_residual"] == pytest.approx(total, abs=1e-12)
    assert document["total_residual"] == pytest.approx(0.0, abs=1e-10)


def test_ceiling_accepts_inside_case(tmp_path):
    """题面：「残差总和未越过上限时 accepted 记作 true。」"""
    payload = base_payload()
    payload["limits"]["residual_ceiling"] = 1.0
    payload["profiles"][0]["fingerprint"] = [value * 1.04 for value in payload["profiles"][0]["fingerprint"]]
    result, _, output = invoke(tmp_path, payload)
    document = read(output)
    assert result.returncode == 0 and document["accepted"] is True
    assert document["status"] == "probes_reconciled"


def test_ceiling_quarantines_first_outside_value(tmp_path):
    """题面：「越线批次继续落盘，令 accepted=false，status=quarantined。」"""
    payload = base_payload()
    payload["limits"]["residual_ceiling"] = 0.0001
    payload["profiles"][0]["fingerprint"] = [value * 1.04 for value in payload["profiles"][0]["fingerprint"]]
    result, _, output = invoke(tmp_path, payload)
    document = read(output)
    assert result.returncode == 0 and document["accepted"] is False
    assert document["status"] == "quarantined"


def test_missing_top_level_key_is_refused(tmp_path):
    """题面：「少一个顶层对象时返回版本 1，并打印 台架拒收: BAD_RIG。」"""
    payload = base_payload()
    payload.pop("limits")
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "台架拒收: BAD_RIG\n" and not output.exists()


def test_extra_top_level_key_is_refused(tmp_path):
    """题面：「多一个顶层对象时返回版本 1，并打印 台架拒收: BAD_RIG。」"""
    payload = base_payload()
    payload["memo"] = "shift"
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "台架拒收: BAD_RIG\n" and not output.exists()


def test_duplicate_top_level_key_is_refused(tmp_path):
    """题面：「同层对象重名按坏导出处理，输出 台架拒收: BAD_RIG。」"""
    payload = base_payload()
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    raw = raw.replace('"rig_id":"', '"rig_id":"duplicate", "rig_id":"', 1) + "\n"
    result, _, output = invoke(tmp_path, raw=raw)
    assert result.returncode == 1 and result.stderr == "台架拒收: BAD_RIG\n" and not output.exists()


def test_boolean_numeric_is_refused(tmp_path):
    """题面：「本应填数处出现 true 或 false 时，不属于有限数，输出 台架拒收: BAD_RIG。」"""
    payload = base_payload()
    payload["readings"][0]["drive_hz"] = True
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "台架拒收: BAD_RIG\n" and not output.exists()


def test_profile_fingerprint_length_is_refused(tmp_path):
    """题面：「三元 fingerprint 中任何分量缺失、为零或非有限，输出 台架拒收: BAD_RIG。」"""
    payload = base_payload()
    payload["profiles"][0]["fingerprint"].pop()
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "台架拒收: BAD_RIG\n" and not output.exists()


def test_duplicate_slot_is_refused(tmp_path):
    """题面：「两条记录共用同一 slot 值时，输出 台架拒收: BAD_RIG。」"""
    payload = base_payload()
    payload["readings"][1]["slot"] = payload["readings"][0]["slot"]
    result, _, output = invoke(tmp_path, payload)
    assert result.returncode == 1 and result.stderr == "台架拒收: BAD_RIG\n" and not output.exists()
    minimum = base_payload()
    minimum["rig_id"] = "AB"
    minimum_result, _, minimum_output = invoke(tmp_path, minimum, output_name="minimum.json")
    assert minimum_result.returncode == 0 and read(minimum_output)["rig_id"] == "AB"
    spaced = base_payload()
    spaced["rig_id"] = "A B"
    spaced_result, _, spaced_output = invoke(tmp_path, spaced, output_name="spaced.json")
    assert spaced_result.returncode == 0 and read(spaced_output)["rig_id"] == "A B"
    control = base_payload()
    control["rig_id"] = "A\tB"
    control_result, _, control_output = invoke(tmp_path, control, output_name="control.json")
    assert control_result.returncode == 1 and control_result.stderr == "台架拒收: BAD_RIG\n" and not control_output.exists()


def test_ledger_has_exact_shape_and_is_idempotent(tmp_path):
    """题面：「同一份输入产生同一结果后重导，留痕文件每个字节都不变。」"""
    ledger = tmp_path / "trail.jsonl"
    result, _, output = invoke(tmp_path, payload=base_payload(), ledger=ledger)
    first = ledger.read_bytes()
    second, _, _ = invoke(tmp_path, payload=base_payload(), ledger=ledger)
    item = json.loads(first)
    assert result.returncode == 0 and second.returncode == 0
    assert list(item) == LEDGER_KEYS and first.endswith(b"\n")
    assert ledger.read_bytes() == first and second.stdout == "" and second.stderr == ""


def test_different_result_appends_one_ledger_line(tmp_path):
    """题面：「新的有效结果出现时，按产生先后在留痕文件尾部续一行。」"""
    ledger = tmp_path / "trail.jsonl"
    first, _, _ = invoke(tmp_path, payload=base_payload(), ledger=ledger)
    changed = base_payload()
    changed["rig_id"] = "RIG-STD-8"
    second, _, _ = invoke(tmp_path, payload=changed, ledger=ledger)
    assert first.returncode == 0 and second.returncode == 0
    assert len(ledger.read_bytes().splitlines()) == 2
    assert ledger.read_bytes().endswith(b"\n")


def test_ledger_path_equal_to_output_is_refused(tmp_path):
    """题面：「结果与留痕指向同一路径时输出 留痕拒收: BAD_RIG_LEDGER。」"""
    payload = base_payload()
    source = tmp_path / "readings.json"
    target = tmp_path / "same.json"
    source.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    result = subprocess.run([sys.executable, ENTRY, str(source), str(target), str(target)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and result.stderr == "留痕拒收: BAD_RIG_LEDGER\n" and not target.exists()


def test_io_failure_preserves_existing_target(tmp_path):
    """题面：「结果目录不可写时输出 归档失败: RIG_IO，并让旧结果留在原位。」"""
    target = tmp_path / "occupied"
    target.mkdir()
    source = tmp_path / "readings.json"
    source.write_text(json.dumps(base_payload(), separators=(",", ":")), encoding="utf-8")
    result = subprocess.run([sys.executable, ENTRY, str(source), str(target)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and result.stderr == "归档失败: RIG_IO\n"
    assert target.exists() and target.is_dir() and not any(target.iterdir()) and "traceback" not in result.stderr.lower()


def test_wrong_argument_count_is_refused(tmp_path):
    """题面：「参数数量不符合输入、结果或可选留痕三种调用形状时，返回 1 并输出 台架拒收: BAD_RIG。」"""
    target = tmp_path / "result.json"
    result = subprocess.run([sys.executable, ENTRY], capture_output=True, text=True, timeout=30)
    assert result.returncode == 1 and result.stderr == "台架拒收: BAD_RIG\n" and not target.exists()
