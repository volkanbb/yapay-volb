import asyncio

from app.agents.orchestrator import Orchestrator, extract_action_plan
from app.agents.tasks import TaskState
from app.ai.base import AIProvider, ChatChunk, ProviderStatus
from app.memory.database import Database


class FakeProvider(AIProvider):
    name = "fake"

    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompts: list[tuple[str, str]] = []

    async def status(self):
        return ProviderStatus("fake", True, True)

    async def stream(self, prompt, system=None):
        self.prompts.append((prompt, system or ""))
        for i in range(0, len(self.reply), 7):
            yield ChatChunk("text", self.reply[i:i + 7])
        yield ChatChunk("done")


class Events:
    def __init__(self, approve: bool = True) -> None:
        self.approve = approve
        self.chat: list[list] = []
        self.states: list[str] = []
        self.spoken: list[str] = []
        self.approvals: list[dict] = []
        self.reminders: list[str] = []
        self.orch: Orchestrator | None = None

    def set_state(self, state, activity): self.states.append(state.value)
    def chat_add(self, role, text):
        self.chat.append([role, text]); return len(self.chat) - 1
    def chat_update(self, index, text, done=False): self.chat[index][1] = text
    def recent_action(self, text, ok): pass
    def request_approval(self, req):
        self.approvals.append(req)
        asyncio.get_running_loop().call_soon(self.orch.resolve_approval, req["id"], self.approve)
    def approval_closed(self, approval_id): pass
    def task_changed(self, task): pass
    def research_saved(self): pass
    def memories_changed(self): pass
    def speak(self, text): self.spoken.append(text)
    def reminder(self, text): self.reminders.append(text)
    def schedules_changed(self): pass


def make(reply="", approve=True):
    ev = Events(approve)
    orch = Orchestrator(Database(":memory:"), FakeProvider(reply), None, ev)
    orch._error_delay = 0
    ev.orch = orch
    return orch, ev


def test_extract_plan():
    text = 'Tamam!\n```volb-actions\n[{"action": "launch_app", "params": {"app": "blender"}, "description": "Blender"}]\n```'
    visible, plan = extract_action_plan(text)
    assert visible == "Tamam!" and plan[0]["params"]["app"] == "blender"
    assert extract_action_plan("```volb-actions\nnot json\n```")[1] == []


async def test_local_intent_no_ai():
    orch, ev = make()
    await orch.handle_input("Volb, RAM kullanımımı göster")
    assert orch.provider.prompts == []
    assert "RAM" in ev.chat[-1][1]
    assert "working" in ev.states and ev.states[-1] == "idle"


async def test_ai_chat_streams_and_persona():
    orch, ev = make("Selam! Ben VOLB.")
    await orch.handle_input("naber volb nasılsın")
    assert ev.chat[-1] == ["assistant", "Selam! Ben VOLB."]
    assert "VOLB" in orch.provider.prompts[0][1]
    assert ev.spoken == ["Selam! Ben VOLB."]
    assert orch.db.recent_messages()[-1]["content"] == "Selam! Ben VOLB."


async def test_ai_plan_requires_approval_and_rejection_blocks(tmp_path, monkeypatch):
    import app.computer.actions as actions
    monkeypatch.setattr(actions, "HOME", tmp_path)
    target = tmp_path / "x"
    reply = f'Klasörü oluşturuyorum.\n```volb-actions\n[{{"action":"create_folder","params":{{"path":"{target}"}},"description":"klasör"}}]\n```'
    orch, ev = make(reply, approve=False)
    await orch.handle_input("bir klasör oluşturur musun lütfen")
    assert ev.approvals and not target.exists()
    task = list(orch.tasks.tasks.values())[-1]
    assert task.steps[0].state == TaskState.CANCELLED.value

    orch, ev = make(reply, approve=True)
    await orch.handle_input("bir klasör oluşturur musun lütfen")
    assert target.is_dir()
    assert list(orch.tasks.tasks.values())[-1].state == TaskState.COMPLETED


async def test_ai_cannot_invent_actions():
    reply = '```volb-actions\n[{"action":"shell","params":{"cmd":"rm -rf /"}}]\n```'
    orch, ev = make(reply)
    await orch.handle_input("temizlik yap")
    task = list(orch.tasks.tasks.values())[-1]
    assert task.state == TaskState.FAILED
    assert "izinsiz" in task.steps[0].result


async def test_remember():
    orch, ev = make()
    await orch.handle_input("Volb, hatırla: en sevdiğim editör Neovim")
    assert orch.db.list_memories()[0]["content"] == "en sevdiğim editör Neovim"
    assert "Neovim" in orch.system_prompt()
