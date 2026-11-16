import asyncio
import datetime as dt

import pytest

from app.agents.scheduler import Scheduler
from app.agents.timeparse import next_occurrence, parse_schedule
from app.memory.database import Database
from tests.test_orchestrator import make

NOW = dt.datetime(2026, 11, 5, 23, 10)  # Thursday


@pytest.mark.parametrize("text,when,repeat,kind,payload", [
    ("10 dakika sonra bana çayı hatırlat", "2026-11-05 23:20", "", "reminder", "çayı"),
    ("Volb, yarın saat 9'da YouTube Music'i aç", "2026-11-06 09:00", "", "command", "YouTube Music'i aç"),
    ("her gün 08:30'da yapay zekâ haberlerini araştır", "2026-11-06 08:30", "daily", "command", "yapay zekâ haberlerini araştır"),
    ("cuma akşam 8'de bana maçı hatırlat", "2026-11-06 20:00", "", "reminder", "maçı"),
    ("12 kasım 14:00'te toplantıyı hatırlat", "2026-11-12 14:00", "", "reminder", "toplantıyı"),
    ("hafta içi her gün sabah 7'de RAM kullanımını göster", "2026-11-06 07:00", "weekdays", "command", "RAM kullanımını göster"),
    ("her pazartesi 10:00'da haftalık raporu hatırlat", "2026-11-09 10:00", "weekly", "reminder", "haftalık raporu"),
    ("1 saat sonra Pear Desktop'ta DEEP CODING listesini aç", "2026-11-06 00:10", "", "command", "Pear Desktop'ta DEEP CODING listesini aç"),
    ("tomorrow at 9 pm open youtube music", "2026-11-06 21:00", "", "command", "open youtube music"),
])
def test_parse(text, when, repeat, kind, payload):
    spec = parse_schedule(text, NOW)
    assert spec is not None
    assert spec.run_at.strftime("%Y-%m-%d %H:%M") == when
    assert (spec.repeat, spec.kind, spec.text) == (repeat, kind, payload)


@pytest.mark.parametrize("text", ["saat kaç", "Google'ı aç", "bugün yapay zekâ haberlerini araştır",
                                  "Volb, RAM kullanımımı göster"])
def test_not_a_schedule(text):
    assert parse_schedule(text, dt.datetime(2026, 11, 5, 8, 0)) is None


async def test_statement_with_time_is_not_scheduled():
    orch, ev = make("Güzel, iyi seyirler!")
    await orch.handle_input("bu akşam film izledim, çok güzeldi")
    assert orch.db.list_schedules() == [] and orch.provider.prompts  # went to the AI instead


def test_next_occurrence_skips_weekend():
    fri = dt.datetime(2026, 11, 6, 7, 0)
    assert next_occurrence(fri, "weekdays", fri).weekday() == 0
    assert next_occurrence(fri, "", fri) is None


async def test_scheduler_fires_and_repeats(tmp_path):
    db = Database(tmp_path / "s.db")
    fired = []

    async def fire(job):
        fired.append(job["payload"])
        return "ok"
    now = dt.datetime(2026, 11, 5, 9, 0)
    once = db.add_schedule("a", "reminder", "tek", (now - dt.timedelta(seconds=30)).timestamp())
    daily = db.add_schedule("b", "command", "her gün", (now - dt.timedelta(seconds=10)).timestamp(), "daily")
    missed = db.add_schedule("c", "reminder", "kaçtı", (now - dt.timedelta(hours=3)).timestamp())
    future = db.add_schedule("d", "reminder", "sonra", (now + dt.timedelta(hours=1)).timestamp())
    sch = Scheduler(db, fire)
    assert await sch.tick(now) == 2
    assert sorted(fired) == ["her gün", "tek"]
    rows = {r["id"]: r for r in db.list_schedules()}
    assert rows[once]["enabled"] == 0 and rows[future]["enabled"] == 1
    assert rows[daily]["enabled"] == 1 and rows[daily]["run_at"] > now.timestamp()
    assert rows[missed]["enabled"] == 0 and "Kaçırıldı" in rows[missed]["last_result"]
    assert await sch.tick(now) == 0     # nothing fires twice


async def test_orchestrator_schedules_locally_and_reminds():
    orch, ev = make()
    await orch.handle_input("Volb, 10 dakika sonra bana çayı hatırlat")
    rows = orch.db.list_schedules()
    assert rows and rows[0]["kind"] == "reminder" and rows[0]["payload"] == "çayı"
    assert not ev.approvals                    # typed by the user → no approval needed
    assert orch.provider.prompts == []         # no AI call
    await orch._fire_schedule(rows[0])
    assert ev.reminders == ["çayı"]


async def test_ai_proposed_schedule_needs_approval():
    reply = ('Tamam.\n```volb-actions\n[{"action":"schedule_task","params":{"when":"2099-01-01T09:00",'
             '"text":"YouTube Music\'i aç","kind":"command"},"description":"zamanla"}]\n```')
    orch, ev = make(reply, approve=False)
    await orch.handle_input("sabahları müzik açsan iyi olur gibi")
    assert ev.approvals and ev.approvals[0]["action"] == "schedule_task"
    assert orch.db.list_schedules() == []


async def test_scheduled_command_runs_through_orchestrator():
    orch, ev = make()
    await orch._fire_schedule({"id": 1, "kind": "command", "payload": "RAM kullanımımı göster"})
    assert any("RAM" in m[1] for m in ev.chat)
