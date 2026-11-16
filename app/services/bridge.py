"""Backend QObject exposed to QML as `backend`.

All worker-thread events are marshalled to the GUI thread through `_post`, so properties are
only ever mutated on the Qt main thread.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import logging
import threading
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from ..agents.orchestrator import Orchestrator
from ..agents.tasks import Task
from ..ai.base import AIProvider
from ..ai.registry import create_provider
from ..browser.controller import BrowserController
from ..browser.research import ResearchService
from ..core.async_runner import AsyncRunner
from ..core.config import APP_NAME, APP_VERSION, DATA_DIR, Settings, load_settings
from ..core.state import AssistantState
from ..computer.system_monitor import gpu_info, read_stats, top_processes
from ..memory.database import Database
from ..memory.semantic import SemanticMemory
from ..voice.audio_io import audio_available, list_input_devices
from ..voice.service import VoiceService

log = logging.getLogger(__name__)


LIMIT_LABELS = {"five_hour": "5 saatlik oturum", "seven_day": "Haftalık", "seven_day_opus": "Haftalık (Opus)",
                "seven_day_sonnet": "Haftalık (Sonnet)"}


def _limit_toast(info: dict[str, Any]) -> str:
    name = LIMIT_LABELS.get(str(info.get("rateLimitType")), str(info.get("rateLimitType")))
    when = dt.datetime.fromtimestamp(info["resetsAt"]).strftime("%H:%M") if info.get("resetsAt") else "?"
    if info.get("status") == "rejected":
        return f"Claude {name} limiti doldu. Sıfırlanma: {when}"
    return f"Claude {name} limitine yaklaşıyorsun. Sıfırlanma: {when}"


def _desktop_notify(title: str, body: str) -> None:
    import shutil
    import subprocess
    if shutil.which("notify-send"):
        try:
            subprocess.Popen(["notify-send", "-a", "YAPAY VOLB", "-u", "critical", title, body],  # noqa: S603
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except OSError:
            pass


def _prop(name: str, typ: Any):
    sig = Signal()

    def getter(self):
        return self._vals[name]

    return sig, Property(typ, getter, notify=sig)


DEFAULTS: dict[str, Any] = {
    "state": "idle", "activity": "Başlatılıyor…", "micLevel": 0.0, "speechLevel": 0.0,
    "cpu": 0.0, "ram": 0.0, "disk": 0.0, "cpuText": "", "ramText": "", "diskText": "", "gpuText": "",
    "uptimeText": "", "claudeConnected": False, "claudeStatus": "Kontrol ediliyor…", "claudeDetail": "",
    "claudeHint": "", "providerName": "", "micStatus": "", "micDevices": [], "listening": False, "speaking": False,
    "continuous": False, "voiceStatus": "", "sttStatus": "", "ttsStatus": "", "activeTask": "Yok",
    "recentActions": [], "tasks": [], "memories": [], "research": [], "approval": {}, "settings": {},
    "browserTabs": [], "browserStatus": "Kapalı", "lastScreenshot": "", "topProcesses": [],
    "cpuHistory": [], "ramHistory": [], "appVersion": APP_VERSION, "busy": False, "lastReply": "", "usage": {}, "rateLimits": [], "limitChecking": False, "schedules": [], "sleepInhibited": False, "sleepReason": "",
}


class Backend(QObject):
    _invoke = Signal(object)

    stateChanged, state = _prop("state", str)
    activityChanged, activity = _prop("activity", str)
    micLevelChanged, micLevel = _prop("micLevel", float)
    speechLevelChanged, speechLevel = _prop("speechLevel", float)
    cpuChanged, cpu = _prop("cpu", float)
    ramChanged, ram = _prop("ram", float)
    diskChanged, disk = _prop("disk", float)
    cpuTextChanged, cpuText = _prop("cpuText", str)
    ramTextChanged, ramText = _prop("ramText", str)
    diskTextChanged, diskText = _prop("diskText", str)
    gpuTextChanged, gpuText = _prop("gpuText", str)
    uptimeTextChanged, uptimeText = _prop("uptimeText", str)
    claudeConnectedChanged, claudeConnected = _prop("claudeConnected", bool)
    claudeStatusChanged, claudeStatus = _prop("claudeStatus", str)
    claudeDetailChanged, claudeDetail = _prop("claudeDetail", str)
    claudeHintChanged, claudeHint = _prop("claudeHint", str)
    providerNameChanged, providerName = _prop("providerName", str)
    micStatusChanged, micStatus = _prop("micStatus", str)
    micDevicesChanged, micDevices = _prop("micDevices", "QVariantList")
    listeningChanged, listening = _prop("listening", bool)
    speakingChanged, speaking = _prop("speaking", bool)
    continuousChanged, continuous = _prop("continuous", bool)
    voiceStatusChanged, voiceStatus = _prop("voiceStatus", str)
    sttStatusChanged, sttStatus = _prop("sttStatus", str)
    ttsStatusChanged, ttsStatus = _prop("ttsStatus", str)
    activeTaskChanged, activeTask = _prop("activeTask", str)
    recentActionsChanged, recentActions = _prop("recentActions", "QVariantList")
    tasksChanged, tasks = _prop("tasks", "QVariantList")
    memoriesChanged, memories = _prop("memories", "QVariantList")
    researchChanged, research = _prop("research", "QVariantList")
    approvalChanged, approval = _prop("approval", "QVariantMap")
    settingsChanged, settings = _prop("settings", "QVariantMap")
    browserTabsChanged, browserTabs = _prop("browserTabs", "QVariantList")
    browserStatusChanged, browserStatus = _prop("browserStatus", str)
    lastScreenshotChanged, lastScreenshot = _prop("lastScreenshot", str)
    topProcessesChanged, topProcesses = _prop("topProcesses", "QVariantList")
    cpuHistoryChanged, cpuHistory = _prop("cpuHistory", "QVariantList")
    ramHistoryChanged, ramHistory = _prop("ramHistory", "QVariantList")
    appVersionChanged, appVersion = _prop("appVersion", str)
    busyChanged, busy = _prop("busy", bool)
    lastReplyChanged, lastReply = _prop("lastReply", str)
    usageChanged, usage = _prop("usage", "QVariantMap")
    rateLimitsChanged, rateLimits = _prop("rateLimits", "QVariantList")
    limitCheckingChanged, limitChecking = _prop("limitChecking", bool)
    schedulesChanged, schedules = _prop("schedules", "QVariantList")
    sleepInhibitedChanged, sleepInhibited = _prop("sleepInhibited", bool)
    sleepReasonChanged, sleepReason = _prop("sleepReason", str)

    toast = Signal(str, str)  # message, kind (info|ok|warn|error)

    def __init__(self, chat_model, parent=None) -> None:
        super().__init__(parent)
        self._vals: dict[str, Any] = {k: (list(v) if isinstance(v, list) else dict(v) if isinstance(v, dict) else v)
                                      for k, v in DEFAULTS.items()}
        self._invoke.connect(self._run_posted, Qt.QueuedConnection)
        self.chat = chat_model
        self._chat_counter = 0
        self._chat_lock = threading.Lock()
        self._base_state = AssistantState.IDLE
        self._preview: str | None = None
        self._fake_speech_timer = QTimer(self, singleShot=True)
        self._fake_speech_timer.timeout.connect(lambda: self._set_voice_flags(None, False))
        self._recent: deque[dict] = deque(maxlen=12)
        self._cpu_hist: deque[float] = deque(maxlen=60)
        self._ram_hist: deque[float] = deque(maxlen=60)
        self._tick = 0

        self.runner = AsyncRunner()
        self.runner.start()
        self.db = Database()
        self.cfg: Settings = load_settings(self.db.load_settings())
        self.semantic = SemanticMemory(self.cfg.semantic_memory)
        self.provider: AIProvider = create_provider(self.cfg)
        self._attach_usage(self.provider)
        self.browser = BrowserController(headless=self.cfg.browser_headless)
        self.research_service = ResearchService(self.browser, lambda: self.provider)
        self.orchestrator = Orchestrator(self.db, self.provider, self.research_service, self, self.semantic)
        self.orchestrator.speak_responses = self.cfg.speak_responses
        self.voice: VoiceService | None = VoiceService(self.cfg, self, self.runner.loop) if audio_available() else None

        self._load_history()
        self._set("settings", self.cfg.public_dict())
        self._set("micDevices", list_input_devices())
        self._refresh_lists()
        self._refresh_usage()
        self._refresh_schedules()
        self._refresh_voice_status()
        self.runner.call_soon(self.orchestrator.start_scheduler)

        from ..computer.power import SleepInhibitor
        self.sleep_guard = SleepInhibitor()
        self._sleep_timer = QTimer(self)
        self._sleep_timer.timeout.connect(self._update_sleep_guard)
        self._sleep_timer.start(30_000)
        QTimer.singleShot(1000, self._update_sleep_guard)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_system)
        self._timer.start(1500)
        self._poll_system()
        self.refreshClaude()
        self._update_state()
        if self.cfg.continuous_listening and self.voice:
            QTimer.singleShot(1500, lambda: self.setContinuous(True))

    # ================================================================== infra
    def _set(self, name: str, value: Any) -> None:
        if self._vals.get(name) != value:
            self._vals[name] = value
            getattr(self, name + "Changed").emit()

    def _post(self, fn: Callable[[], None]) -> None:
        if threading.current_thread() is threading.main_thread():
            fn()
        else:
            self._invoke.emit(fn)

    @Slot(object)
    def _run_posted(self, fn) -> None:
        try:
            fn()
        except Exception:  # noqa: BLE001
            log.exception("posted callback failed")

    def _submit(self, coro) -> None:
        self.runner.submit(coro)

    def _update_state(self) -> None:
        if self._preview:
            state = self._preview
        elif self._base_state == AssistantState.ERROR:
            state = "error"
        elif self._vals["speaking"]:
            state = "speaking"
        elif self._vals["listening"]:
            state = "listening"
        else:
            state = self._base_state.value
        self._set("state", state)
        self._set("busy", self._base_state in (AssistantState.THINKING, AssistantState.WORKING))

    def _load_history(self) -> None:
        for m in self.db.recent_messages(40):
            self.chat.append(m["role"], m["content"], True, m["created_at"])
            if m["role"] == "assistant":
                self._vals["lastReply"] = m["content"]
        self._chat_counter = self.chat.count()

    def _refresh_lists(self) -> None:
        mems = [{"id": m["id"], "content": m["content"], "category": m["category"],
                 "date": dt.datetime.fromtimestamp(m["updated_at"]).strftime("%d.%m.%Y %H:%M")}
                for m in self.db.list_memories()]
        self._set("memories", mems)
        res = [{"id": r["id"], "topic": r["topic"], "report": r["report"], "sources": r["sources"],
                "date": dt.datetime.fromtimestamp(r["created_at"]).strftime("%d.%m.%Y %H:%M")}
               for r in self.db.list_research()]
        self._set("research", res)
        self._set("tasks", self.orchestrator.tasks.history())
        if not self._recent:
            for a in reversed(self.db.recent_actions(8)):
                self._recent.appendleft({"text": f"{a['action']}: {a['message'][:60]}", "ok": bool(a["ok"]),
                                         "time": dt.datetime.fromtimestamp(a["created_at"]).strftime("%H:%M")})
            self._set("recentActions", list(self._recent))

    def _refresh_voice_status(self) -> None:
        if not self.voice:
            self._set("micStatus", "Ses sistemi bulunamadı")
            self._set("sttStatus", "—")
            self._set("ttsStatus", "—")
            return
        st = self.voice.status()
        self._set("micStatus", st.mic)
        self._set("sttStatus", st.stt)
        self._set("ttsStatus", st.tts)

    def _poll_system(self) -> None:
        s = read_stats()
        self._set("cpu", s.cpu / 100)
        self._set("ram", s.ram / 100)
        self._set("disk", s.disk / 100)
        self._set("cpuText", f"%{s.cpu:.0f} • {s.cpu_count} çekirdek")
        self._set("ramText", f"{s.ram_used_gb:.1f} / {s.ram_total_gb:.1f} GB")
        self._set("diskText", f"{s.disk_used_gb:.0f} / {s.disk_total_gb:.0f} GB")
        self._set("uptimeText", f"{s.uptime_h:.1f} sa")
        self._cpu_hist.append(s.cpu / 100)
        self._ram_hist.append(s.ram / 100)
        self._set("cpuHistory", list(self._cpu_hist))
        self._set("ramHistory", list(self._ram_hist))
        if self._tick % 4 == 0:
            async def _slow() -> None:
                gpu = await asyncio.to_thread(gpu_info)
                procs = await asyncio.to_thread(top_processes, 7)
                self._post(lambda: (self._set("gpuText", gpu), self._set("topProcesses", procs)))
            self._submit(_slow())
        self._tick += 1

    # ================================================================== AI usage / limits
    def _attach_usage(self, provider: AIProvider) -> None:
        def on_usage(rec: dict[str, Any]) -> None:
            self.db.log_usage(rec)
            self._post(self._refresh_usage)

        def on_limit(info: dict[str, Any]) -> None:
            self.db.save_rate_limit(info)
            self._post(self._refresh_usage)
            if info.get("status") not in (None, "allowed"):
                kind = "error" if info.get("status") == "rejected" else "warn"
                self._post(lambda: self.toast.emit(_limit_toast(info), kind))

        provider.usage_sink = on_usage
        provider.limit_sink = on_limit

    def _refresh_usage(self) -> None:
        summary = self.db.usage_summary()
        for r in summary["recent"]:
            r["time"] = dt.datetime.fromtimestamp(r.pop("created_at")).strftime("%d.%m %H:%M")
        self._set("usage", summary)
        self._set("rateLimits", self.db.rate_limits())

    # ================================================================== OrchestratorEvents
    def set_state(self, state: AssistantState, activity: str) -> None:
        def apply() -> None:
            self._base_state = state
            self._set("activity", activity)
            active = self.orchestrator.tasks.active()
            self._set("activeTask", active.title if active else "Yok")
            self._update_state()
        self._post(apply)

    def chat_add(self, role: str, text: str) -> int:
        with self._chat_lock:
            idx = self._chat_counter
            self._chat_counter += 1
        def apply() -> None:
            self.chat.append(role, text, done=bool(text) or role == "user")
            if role == "assistant":
                self._set("lastReply", text)
        self._post(apply)
        return idx

    def chat_update(self, index: int, text: str, done: bool = False) -> None:
        def apply() -> None:
            self.chat.update(index, text, done)
            self._set("lastReply", text)
        self._post(apply)

    def recent_action(self, text: str, ok: bool) -> None:
        def apply() -> None:
            self._recent.appendleft({"text": text, "ok": ok, "time": dt.datetime.now().strftime("%H:%M")})
            self._set("recentActions", list(self._recent))
        self._post(apply)

    def request_approval(self, request: dict[str, Any]) -> None:
        self._post(lambda: self._set("approval", request))

    def approval_closed(self, approval_id: str) -> None:
        def apply() -> None:
            if self._vals["approval"].get("id") == approval_id:
                self._set("approval", {})
        self._post(apply)

    def task_changed(self, task: Task) -> None:
        def apply() -> None:
            self._set("tasks", self.orchestrator.tasks.history())
            active = self.orchestrator.tasks.active()
            self._set("activeTask", active.title if active else "Yok")
        self._post(apply)

    def research_saved(self) -> None:
        self._post(self._refresh_lists)

    def memories_changed(self) -> None:
        self._post(self._refresh_lists)

    def speak(self, text: str) -> None:
        def apply() -> None:
            if not self.cfg.speak_responses:
                return
            if self.voice and self.voice.tts.name != "none":
                self._submit(self.voice.speak(text))
            else:
                # No TTS engine: VOLB still "talks" visually for a moment.
                self._set_voice_flags(None, True)
                self._fake_speech_timer.start(int(min(max(len(text) * 45, 1200), 7000)))
        self._post(apply)

    def reminder(self, text: str) -> None:
        def apply() -> None:
            msg = f"⏰ Hatırlatma: {text}"
            self.chat_add("assistant", msg)
            self.db.add_message("assistant", msg)
            self.toast.emit(msg, "warn")
            self.speak(f"Hatırlatma: {text}")
            _desktop_notify("YAPAY VOLB — Hatırlatma", text)
        self._post(apply)

    def schedules_changed(self) -> None:
        self._post(lambda: (self._refresh_schedules(), self._update_sleep_guard()))

    def _update_sleep_guard(self) -> None:
        """Block automatic sleep according to settings (manual sleep / lid close still work)."""
        import time as _time

        from ..computer.power import desired_reason
        runs = [r["run_at"] for r in self.db.list_schedules() if r["enabled"]]
        reason = desired_reason(self.cfg.sleep_inhibit, runs, _time.time())
        if reason:
            ok = self.sleep_guard.inhibit(reason)
        else:
            self.sleep_guard.release()
            ok = False
        self._set("sleepInhibited", ok)
        self._set("sleepReason", reason if ok else "")

    def _refresh_schedules(self) -> None:
        rows = []
        for r in self.db.list_schedules():
            rows.append({**r, "when": dt.datetime.fromtimestamp(r["run_at"]).strftime("%d.%m.%Y %H:%M"),
                         "lastRun": dt.datetime.fromtimestamp(r["last_run"]).strftime("%d.%m %H:%M") if r["last_run"] else "",
                         "last_result": r["last_result"] or ""})
        self._set("schedules", rows)

    # ================================================================== VoiceEvents
    def on_mic_level(self, level: float) -> None:
        self._post(lambda: self._set("micLevel", round(level, 3)))

    def on_speech_level(self, level: float) -> None:
        self._post(lambda: self._set("speechLevel", round(level, 3)))

    def _set_voice_flags(self, listening: bool | None, speaking: bool | None) -> None:
        if listening is not None:
            self._set("listening", listening)
        if speaking is not None:
            self._set("speaking", speaking)
        self._update_state()

    def on_voice_state(self, listening: bool, speaking: bool, status: str) -> None:
        def apply() -> None:
            self._set_voice_flags(listening, speaking)
            if status:
                self._set("voiceStatus", status)
        self._post(apply)

    def on_voice_command(self, text: str, language: str) -> None:
        def apply() -> None:
            self._set("voiceStatus", f"Duyulan ({language}): {text}")
            self.stopSpeaking()
            self._submit(self.orchestrator.handle_input(text, source="voice"))
        self._post(apply)

    def on_voice_error(self, message: str) -> None:
        def apply() -> None:
            self._set_voice_flags(False, False)
            self._set("voiceStatus", message)
            self.toast.emit(message, "error")
        self._post(apply)

    # ================================================================== QML slots
    @Slot(str)
    def sendText(self, text: str) -> None:  # noqa: N802
        if text.strip():
            self.stopSpeaking()
            self._submit(self.orchestrator.handle_input(text, source="text"))

    @Slot()
    def pttPressed(self) -> None:  # noqa: N802
        if not self.voice:
            self.toast.emit("Mikrofon kullanılamıyor.", "error")
            return
        self.voice.start_push_to_talk()

    @Slot()
    def pttReleased(self) -> None:  # noqa: N802
        if self.voice:
            self.voice.stop_push_to_talk()
            self._set_voice_flags(False, None)

    @Slot(bool)
    def setContinuous(self, enabled: bool) -> None:  # noqa: N802
        if not self.voice:
            self.toast.emit("Mikrofon kullanılamıyor.", "error")
            return
        self.voice.set_continuous(enabled)
        self._set("continuous", enabled)

    @Slot()
    def stopSpeaking(self) -> None:  # noqa: N802
        if self.voice:
            self.voice.stop_speaking()
        self._fake_speech_timer.stop()
        self._set_voice_flags(None, False)

    @Slot()
    def stopAll(self) -> None:  # noqa: N802
        self.stopSpeaking()
        self._submit(self.orchestrator.stop())
        self.set_state(AssistantState.IDLE, "Durduruldu")

    @Slot(str, bool)
    def resolveApproval(self, approval_id: str, approved: bool) -> None:  # noqa: N802
        self.runner.call_soon(self.orchestrator.resolve_approval, approval_id, approved)
        self._set("approval", {})

    @Slot(str)
    def cancelTask(self, task_id: str) -> None:  # noqa: N802
        def _cancel() -> None:
            self.orchestrator.tasks.cancel(task_id)
            for fut in list(self.orchestrator._approvals.values()):
                if not fut.done():
                    fut.set_result(False)
        self.runner.call_soon(_cancel)

    @Slot()
    def refreshClaude(self) -> None:  # noqa: N802
        self._set("claudeStatus", "Kontrol ediliyor…")

        async def _check() -> None:
            st = await self.provider.status()
            def apply() -> None:
                self._set("providerName", self.provider.display_name)
                self._set("claudeConnected", st.ready)
                self._set("claudeStatus", ("Bağlı" if st.ready else "Bağlı değil") +
                          (f" • v{st.version}" if st.version else ""))
                self._set("claudeDetail", st.detail)
                self._set("claudeHint", st.install_hint or "")
                if self._base_state == AssistantState.IDLE:
                    self._set("activity", "Hazır" if st.ready else "Claude bağlantısı bekleniyor")
            self._post(apply)
        self._submit(_check())

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value: Any) -> None:  # noqa: N802
        if key not in Settings.model_fields:
            return
        try:
            data = self.cfg.model_dump()
            data[key] = value
            new = Settings.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            self.toast.emit(f"Geçersiz ayar: {exc}", "error")
            return
        if key == "allow_paid_api" and value:
            self.toast.emit("Ücretli API izni açıldı. Bu, Claude Pro'dan AYRI faturalandırılır.", "warn")
        self.cfg = new
        self.db.save_setting(key, getattr(new, key))
        self._set("settings", new.public_dict())
        if key in ("ai_provider", "claude_model", "ollama_model", "allow_paid_api"):
            self.provider = create_provider(new)
            self._attach_usage(self.provider)
            self.orchestrator.provider = self.provider
            self.refreshClaude()
        if key == "speak_responses":
            self.orchestrator.speak_responses = bool(value)
        if self.voice:
            self.voice.settings = new
            if key in ("tts_engine", "piper_voice", "edge_voice", "allow_edge_tts"):
                self.voice.reload_tts(new)
            if key == "mic_device":
                self.voice.set_device(int(value))
            if key in ("stt_model", "stt_device"):
                self.voice = VoiceService(new, self, self.runner.loop)
            if key == "wake_word":
                from ..voice.wakeword import TranscriptWakeWord
                self.voice.wake = TranscriptWakeWord(str(value))
        if key == "sleep_inhibit":
            self._update_sleep_guard()
        if key == "browser_headless":
            self.browser.headless = bool(value)
        self._refresh_voice_status()

    @Slot(str)
    def addMemory(self, text: str) -> None:  # noqa: N802
        if text.strip():
            mid = self.db.add_memory(text.strip(), "kullanıcı")
            self.semantic.upsert(mid, text.strip())
            self._refresh_lists()

    @Slot(int, str)
    def updateMemory(self, mem_id: int, text: str) -> None:  # noqa: N802
        self.db.update_memory(mem_id, text)
        self.semantic.upsert(mem_id, text)
        self._refresh_lists()

    @Slot(int)
    def deleteMemory(self, mem_id: int) -> None:  # noqa: N802
        self.db.delete_memory(mem_id)
        self.semantic.delete(mem_id)
        self._refresh_lists()

    @Slot(int)
    def deleteResearch(self, rid: int) -> None:  # noqa: N802
        self.db.delete_research(rid)
        self._refresh_lists()

    @Slot(result=str)
    def exportMemory(self) -> str:  # noqa: N802
        path = self.db.export_all(DATA_DIR / "exports" / f"volb_export_{dt.datetime.now():%Y%m%d_%H%M%S}.json")
        self.toast.emit(f"Dışa aktarıldı: {path.name}", "ok")
        return str(path)

    @Slot()
    def wipePersonalData(self) -> None:  # noqa: N802
        self.db.wipe_personal_data()
        self.chat.clear()
        with self._chat_lock:
            self._chat_counter = 0
        self.provider.reset_conversation()
        self._recent.clear()
        self._set("recentActions", [])
        self._refresh_lists()
        self.toast.emit("Tüm kişisel veriler silindi.", "ok")

    @Slot()
    def clearChat(self) -> None:  # noqa: N802
        self.db.clear_conversations()
        self.chat.clear()
        with self._chat_lock:
            self._chat_counter = 0
        self.provider.reset_conversation()

    @Slot(str)
    def runResearch(self, topic: str) -> None:  # noqa: N802
        if topic.strip():
            self.sendText(f"{topic.strip()} araştır")

    @Slot(str)
    def browserOpen(self, url: str) -> None:  # noqa: N802
        async def _go() -> None:
            try:
                self._post(lambda: self._set("browserStatus", "Açılıyor…"))
                await self.browser.new_tab(url)
                await self._refresh_tabs()
            except Exception as exc:  # noqa: BLE001
                self._post(lambda: (self._set("browserStatus", "Hata"), self.toast.emit(str(exc)[:300], "error")))
        self._submit(_go())

    async def _refresh_tabs(self) -> None:
        tabs = await self.browser.tab_titles()
        self._post(lambda: (self._set("browserTabs", tabs),
                            self._set("browserStatus", f"Çalışıyor • {len(tabs)} sekme" if self.browser.running
                                      else "Kapalı")))

    @Slot()
    def browserRefresh(self) -> None:  # noqa: N802
        self._submit(self._refresh_tabs())

    @Slot(int)
    def browserCloseTab(self, index: int) -> None:  # noqa: N802
        async def _close() -> None:
            await self.browser.close_tab(index)
            await self._refresh_tabs()
        self._submit(_close())

    @Slot(int)
    def browserScreenshot(self, index: int) -> None:  # noqa: N802
        async def _shot() -> None:
            ctx = self.browser._context
            if not ctx or not ctx.pages:
                self._post(lambda: self.toast.emit("Açık sekme yok.", "warn"))
                return
            page = ctx.pages[min(max(index, 0), len(ctx.pages) - 1)]
            path = await self.browser.screenshot(page)
            self._post(lambda: (self._set("lastScreenshot", QUrl.fromLocalFile(path).toString()),
                                self.toast.emit("Sayfa görüntüsü alındı.", "ok")))
        self._submit(_shot())

    @Slot()
    def browserStop(self) -> None:  # noqa: N802
        async def _stop() -> None:
            await self.browser.stop()
            await self._refresh_tabs()
        self._submit(_stop())

    @Slot(int)
    def deleteSchedule(self, sid: int) -> None:  # noqa: N802
        self.db.delete_schedule(sid)
        self._refresh_schedules()

    @Slot(int, bool)
    def setScheduleEnabled(self, sid: int, enabled: bool) -> None:  # noqa: N802
        self.db.update_schedule(sid, enabled=int(enabled))
        self._refresh_schedules()

    @Slot(int)
    def runScheduleNow(self, sid: int) -> None:  # noqa: N802
        job = next((r for r in self.db.list_schedules() if r["id"] == sid), None)
        if job:
            self._submit(self.orchestrator._fire_schedule(job))

    @Slot()
    def refreshUsage(self) -> None:  # noqa: N802
        self._refresh_usage()

    @Slot()
    def probeLimits(self) -> None:  # noqa: N802
        probe = getattr(self.provider, "probe_limits", None)
        if probe is None:
            self.toast.emit("Bu sağlayıcı limit bilgisi vermiyor.", "warn")
            return
        self._set("limitChecking", True)

        async def _run() -> None:
            try:
                await probe()
                self._post(lambda: self.toast.emit("Limit durumu güncellendi.", "ok"))
            except Exception as exc:  # noqa: BLE001
                self._post(lambda: self.toast.emit(f"Limit kontrolü başarısız: {exc}", "error"))
            finally:
                self._post(lambda: self._set("limitChecking", False))
        self._submit(_run())

    @Slot(str)
    def previewState(self, name: str) -> None:  # noqa: N802
        """Preview a character animation state (Settings → Animasyon önizleme)."""
        self._preview = name or None
        self._update_state()

    @Slot(str)
    def openPath(self, path: str) -> None:  # noqa: N802
        url = QUrl(path) if "://" in path else QUrl.fromLocalFile(path)
        QDesktopServices.openUrl(url)

    @Slot(str)
    def openExternal(self, url: str) -> None:  # noqa: N802
        if url.startswith(("http://", "https://")):
            QDesktopServices.openUrl(QUrl(url))

    @Slot(result=str)
    def appTitle(self) -> str:  # noqa: N802
        return APP_NAME

    # ================================================================== shutdown
    def shutdown(self) -> None:
        self._timer.stop()
        self._sleep_timer.stop()
        self.sleep_guard.release()
        if self.voice:
            self.voice.shutdown()

        async def _close() -> None:
            await self.provider.cancel()
            await self.browser.stop()
        try:
            self.runner.submit(_close()).result(5)
        except Exception:  # noqa: BLE001
            pass
        self.runner.stop()
        self.db.close()
        log.info("VOLB kapandı.")


__all__ = ["Backend", "Path"]
