from app.computer.power import desired_reason
from app.core.config import Settings

NOW = 1_000_000.0


def test_modes():
    assert desired_reason("off", [NOW + 60], NOW) == ""
    assert desired_reason("always", [], NOW) != ""
    assert desired_reason("schedules", [], NOW) == ""
    assert desired_reason("schedules", [NOW + 20 * 60], NOW) != ""       # due in 20 min → block
    assert desired_reason("schedules", [NOW + 3 * 3600], NOW) == ""      # far away → allow sleep


def test_setting_validated():
    import pytest
    assert Settings().sleep_inhibit == "always"
    with pytest.raises(Exception):
        Settings(sleep_inhibit="forever")
