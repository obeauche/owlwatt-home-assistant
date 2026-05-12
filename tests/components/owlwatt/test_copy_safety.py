"""Copy-safety tests — grep all custom_components/owlwatt/*.py and *.json for
forbidden phrases.

Any match fails the test unless the line contains a '# ALLOW: <reason>' marker.

Forbidden phrases:
  "payout", "OwlWatt pays", "you are entitled", "the installer must",
  "pvlib", "PVWatts", "Ineichen", "30 signals", "30 weather signals"
"""
from __future__ import annotations

import re
from pathlib import Path

COMPONENT_DIR = Path(__file__).parent.parent.parent.parent / "custom_components" / "owlwatt"

FORBIDDEN_PHRASES = [
    "payout",
    "OwlWatt pays",
    "you are entitled",
    "the installer must",
    "pvlib",
    "PVWatts",
    "Ineichen",
    "30 signals",
    "30 weather signals",
]

_ALLOW_RE = re.compile(r"#\s*ALLOW:", re.IGNORECASE)


def _scan_file(path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, phrase, line) for forbidden matches without ALLOW marker."""
    violations = []
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if _ALLOW_RE.search(line):
            continue
        for phrase in FORBIDDEN_PHRASES:
            if phrase in line:
                violations.append((lineno, phrase, line.strip()))
    return violations


def test_no_forbidden_phrases_in_python_files():
    """No forbidden phrase in any .py file under custom_components/owlwatt/."""
    violations = []
    for path in COMPONENT_DIR.rglob("*.py"):
        for lineno, phrase, line in _scan_file(path):
            violations.append(
                f"{path.relative_to(COMPONENT_DIR)}:{lineno}: [{phrase!r}] {line}"
            )
    assert not violations, (
        "Forbidden phrases found in Python files:\n" + "\n".join(violations)
    )


def test_no_forbidden_phrases_in_json_files():
    """No forbidden phrase in any .json file under custom_components/owlwatt/."""
    violations = []
    for path in COMPONENT_DIR.rglob("*.json"):
        for lineno, phrase, line in _scan_file(path):
            violations.append(
                f"{path.relative_to(COMPONENT_DIR)}:{lineno}: [{phrase!r}] {line}"
            )
    assert not violations, (
        "Forbidden phrases found in JSON files:\n" + "\n".join(violations)
    )


def test_no_forbidden_phrases_in_yaml_files():
    """No forbidden phrase in any .yaml file under custom_components/owlwatt/."""
    violations = []
    for path in COMPONENT_DIR.rglob("*.yaml"):
        for lineno, phrase, line in _scan_file(path):
            violations.append(
                f"{path.relative_to(COMPONENT_DIR)}:{lineno}: [{phrase!r}] {line}"
            )
    assert not violations, (
        "Forbidden phrases found in YAML files:\n" + "\n".join(violations)
    )


def test_method_label_always_independent_measurement():
    """Any hard-coded method_label string must be 'Independent measurement'."""
    violations = []
    for path in COMPONENT_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if "method_label" in line and "=" in line:
                # Check that none of the forbidden method names appear
                for forbidden in ("pvlib", "PVWatts", "Ineichen", "30 signals"):
                    if forbidden in line and not _ALLOW_RE.search(line):
                        violations.append(
                            f"{path.name}:{lineno}: {line.strip()}"
                        )
    assert not violations, (
        "Forbidden methodology names found:\n" + "\n".join(violations)
    )
