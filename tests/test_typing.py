"""The mypy baseline only shrinks: type a module, then delete it from pyproject.toml."""
import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
# Lower this as modules are typed; raising it fails the test.
MAX_BASELINE = 98


def _config():
    with open(ROOT / 'pyproject.toml', 'rb') as f:
        return tomllib.load(f)['tool']['mypy']


def _baseline():
    for override in _config()['overrides']:
        if override.get('ignore_errors'):
            return override['module']
    raise AssertionError('no baseline override in pyproject.toml')


def test_baseline_does_not_grow():
    assert len(_baseline()) <= MAX_BASELINE, 'type a module instead of adding to the baseline'


def test_baseline_modules_exist():
    missing = [m for m in _baseline() if importlib.util.find_spec(m) is None]
    assert not missing


def test_untyped_calls_exclude_matches_baseline():
    assert sorted(_config()['untyped_calls_exclude']) == sorted(_baseline())


def test_py_typed_ships():
    assert (ROOT / 'abmatt' / 'py.typed').exists()
    assert 'py.typed' in (ROOT / 'setup.py').read_text()


def test_mypy_clean():
    pytest.importorskip('mypy')
    result = subprocess.run([sys.executable, '-m', 'mypy'], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
