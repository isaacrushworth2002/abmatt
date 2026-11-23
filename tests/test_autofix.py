import pytest

from abmatt.autofix import AutoFix, Bug, _AutoFix


@pytest.fixture
def restore_fix_level():
    level = AutoFix.fix_level
    yield
    AutoFix.fix_level = level


def test_set_fix_level_by_name(restore_fix_level):
    AutoFix.set_fix_level('prompt')
    assert AutoFix.fix_level == AutoFix.FIX_PROMPT
    AutoFix.set_fix_level('none')
    assert AutoFix.fix_level == 0


def test_prompt_without_proposed_fix(monkeypatch):
    asked = []
    monkeypatch.setattr('builtins.input', lambda text: asked.append(text) or 'y')
    assert AutoFix.prompt('bad thing') == 1
    assert asked == ['Fix: bad thing? (y/n)']


def test_display_result_without_fix_des(monkeypatch):
    messages = []
    monkeypatch.setattr(AutoFix, 'info', lambda message, loudness=3: messages.append(message))
    bug = Bug(1, 0, 'bad thing')
    AutoFix.display_result(bug)
    assert messages[-1] == '(SUCCESS) bad thing'


def test_get_after_quit(monkeypatch):
    monkeypatch.setattr(_AutoFix, '_AutoFix__AUTO_FIXER', None)
    fixer = AutoFix.get()
    assert isinstance(fixer, _AutoFix)
    assert AutoFix.get() is fixer


def test_prompt_asks_again_on_empty_input(monkeypatch):
    answers = iter(['', 'n'])
    monkeypatch.setattr('builtins.input', lambda text: next(answers))
    assert AutoFix.prompt('bad thing') == 0
