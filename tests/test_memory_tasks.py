import json

from app.agents.tasks import TaskManager, TaskState, TaskStep
from app.memory.database import Database


def test_database_roundtrip(tmp_path):
    db = Database(tmp_path / "t.db")
    db.add_message("user", "selam")
    mid = db.add_memory("kahveyi şekersiz içerim")
    db.update_memory(mid, "kahveyi sade içerim")
    db.save_research("konu", "rapor", [{"index": 1, "title": "t", "url": "https://a"}])
    db.save_setting("tts_engine", "edge")
    db.set_preference("tema", "koyu")
    assert db.list_memories()[0]["content"] == "kahveyi sade içerim"
    assert db.list_research()[0]["sources"][0]["url"] == "https://a"
    assert db.load_settings() == {"tts_engine": "edge"}
    out = db.export_all(tmp_path / "exp.json")
    data = json.loads(out.read_text())
    assert data["conversations"][0]["content"] == "selam" and data["preferences"]["tema"] == "koyu"
    db.wipe_personal_data()
    assert db.list_memories() == [] and db.recent_messages() == []
    assert db.load_settings()  # settings survive a personal-data wipe


def test_task_lifecycle(tmp_path):
    db = Database(tmp_path / "t.db")
    tm = TaskManager(db)
    seen = []
    tm.subscribe(lambda t: seen.append(t.state))
    task = tm.create("deneme", [TaskStep("a", "system_stats"), TaskStep("b", "current_time")])
    tm.set_state(task, TaskState.RUNNING)
    tm.set_step(task, 0, TaskState.COMPLETED, "ok")
    assert task.progress == 0.5
    tm.cancel(task.id)
    assert task.state == TaskState.CANCELLED and task.steps[1].state == "cancelled"
    tm.set_state(task, TaskState.RUNNING)          # terminal states are sticky
    assert task.state == TaskState.CANCELLED
    assert db.list_tasks()[0]["state"] == "cancelled"
    assert TaskState.RUNNING in seen
