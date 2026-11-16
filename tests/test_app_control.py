"""In-app agent loop with a fake accessibility tree (no real desktop needed)."""
import json

import pytest

import app.agents.orchestrator as orch_mod
from app.agents.intent import parse_compound
from app.computer.ui_control import UIElement, is_dangerous
from tests.test_orchestrator import FakeProvider, make


class ScriptedProvider(FakeProvider):
    def __init__(self, steps):
        super().__init__("")
        self.steps = list(steps)

    async def oneshot(self, prompt, system=None, model=None):
        self.prompts.append((prompt, system or ""))
        return json.dumps(self.steps.pop(0))


@pytest.fixture()
def fake_ui(monkeypatch):
    clicks = []
    tree = [UIElement(1, "link", "Kitaplık"), UIElement(2, "link", "DEEP CODING Kullanici adlı içeriği oynat"),
            UIElement(3, "push button", "Çalma listesini sil")]
    ui = orch_mod.ui_control
    monkeypatch.setattr(ui, "available", lambda: (True, ""))
    monkeypatch.setattr(ui, "ensure_accessibility_bus", lambda: True)
    monkeypatch.setattr(ui, "find_app", lambda entry, name: object())
    monkeypatch.setattr(ui, "snapshot", lambda app, limit=140: tree[:limit])
    monkeypatch.setattr(ui, "click", lambda el: clicks.append(el.name) or True)
    monkeypatch.setattr(orch_mod.asyncio, "sleep", _nosleep)
    return clicks


async def _nosleep(*_a, **_k):
    return None


async def test_agent_clicks_playlist(fake_ui):
    orch, ev = make()
    orch.provider = ScriptedProvider([{"action": "click", "id": 2}, {"action": "done", "say": "DEEP CODING çalıyor"}])
    res = await orch._app_control_action(orch_mod.AppControlParams(app="youtube music", goal="DEEP CODING listesini çal"))
    assert res.ok and res.message == "DEEP CODING çalıyor"
    assert fake_ui == ["DEEP CODING Kullanici adlı içeriği oynat"]
    assert "<ui>" in orch.provider.prompts[0][0] and "GÜVENİLMEZ" in orch.provider.prompts[0][0]


async def test_dangerous_click_needs_approval(fake_ui):
    orch, ev = make(approve=False)
    orch.provider = ScriptedProvider([{"action": "click", "id": 3}])
    res = await orch._app_control_action(orch_mod.AppControlParams(app="youtube music", goal="listeyi temizle"))
    assert not res.ok and ev.approvals and fake_ui == []


def test_dangerous_words():
    assert is_dangerous(UIElement(1, "push button", "Çalma listesini sil"))
    assert is_dangerous(UIElement(1, "push button", "Satın al"))
    assert not is_dangerous(UIElement(1, "link", "DEEP CODING adlı içeriği oynat"))


def test_compound_intents():
    steps = parse_compound("Volb, Firefox'u aç ve github'a git")
    assert [s.action for s in steps] == ["launch_app", "app_control"] and steps[1].params["goal"] == "github'a git"
    assert parse_compound("Volb, Google'ı aç") is None
    assert parse_compound("masaüstünde Projeler klasörü oluştur") is None


async def test_stale_element_is_refound_and_retried(fake_ui, monkeypatch):
    ui = orch_mod.ui_control
    calls = {"n": 0}

    def flaky_click(el):
        calls["n"] += 1
        if calls["n"] == 1:
            raise ui.StaleElement(el.name)   # Chromium re-rendered the node
        fake_ui.append(el.name)
        return True
    monkeypatch.setattr(ui, "click", flaky_click)
    monkeypatch.setattr(ui, "refind", lambda app, el: UIElement(99, el.role, el.name))
    orch, ev = make()
    orch.provider = ScriptedProvider([{"action": "click", "id": 2}, {"action": "done", "say": "ok"}])
    res = await orch._app_control_action(orch_mod.AppControlParams(app="youtube music", goal="GRRR PAOWW çal"))
    assert res.ok and fake_ui == ["DEEP CODING Kullanici adlı içeriği oynat"] and calls["n"] == 2


async def test_unexpected_step_error_does_not_kill_task(fake_ui, monkeypatch):
    ui = orch_mod.ui_control
    monkeypatch.setattr(ui, "click", lambda el: (_ for _ in ()).throw(RuntimeError("atspi_error: boom")))
    orch, ev = make()
    orch.provider = ScriptedProvider([{"action": "click", "id": 1}, {"action": "fail", "say": "olmadı"}])
    res = await orch._app_control_action(orch_mod.AppControlParams(app="youtube music", goal="listeyi aç"))
    assert not res.ok and res.message == "olmadı"
    assert "hata" in orch.provider.prompts[1][0]      # the error was reported back to the model


def test_click_raises_stale_on_missing_object():
    from app.computer import ui_control

    class Gone:
        def get_action_iface(self):
            raise RuntimeError('atspi_error: ... object /org/a11y/atspi/accessible/9 does not exist (1)')
    with pytest.raises(ui_control.StaleElement):
        ui_control.click(UIElement(1, "link", "GRRR PAOWW", obj=Gone()))
