import pytest

import app.computer.apps as apps
from app.agents.intent import parse_intent
from app.computer.actions import build_default_registry, resolve_app
from app.security.policy import Risk

ENTRIES = {
    "youtube-music-for-desktop.desktop": "Name=YouTube Music for Desktop\nExec=youtube-music-for-desktop %U\nCategories=AudioVideo;",
    "com.github.th-ch.youtube-music.desktop": "Name=Pear Desktop\nExec=pear-desktop\nCategories=AudioVideo;",
    "org.kde.konsole.desktop": "Name=Konsole\nExec=konsole\nCategories=Qt;KDE;System;TerminalEmulator;",
    "Alacritty.desktop": "Name=Alacritty\nExec=alacritty\nCategories=System;TerminalEmulator;",
    "systemsettings.desktop": "Name=System Settings\nName[tr]=Sistem Ayarları\nExec=systemsettings\nCategories=Qt;KDE;Settings;",
    "gparted.desktop": "Name=GParted\nExec=pkexec gparted\nCategories=System;Filesystem;",
    "blender.desktop": "Name=Blender\nExec=blender %f\nCategories=Graphics;",
    "hidden.desktop": "Name=Gizli\nExec=x\nNoDisplay=true",
    "link.desktop": "Name=Bir Link\nType=Link\nURL=https://x",
}


@pytest.fixture(autouse=True)
def fake_catalog(tmp_path, monkeypatch):
    for fname, body in ENTRIES.items():
        typ = "" if "Type=" in body else "Type=Application\n"
        (tmp_path / fname).write_text(f"[Desktop Entry]\n{typ}{body}\n", encoding="utf-8")
    monkeypatch.setattr(apps, "CATALOG", apps.AppCatalog([tmp_path]))
    monkeypatch.setattr(apps, "is_running", lambda app: False)
    monkeypatch.setattr(apps.shutil, "which", lambda x: f"/usr/bin/{x}" if x == "gtk-launch" else None)


def test_catalog_filters():
    names = {a.name for a in apps.CATALOG.apps()}
    assert "Gizli" not in names and "Bir Link" not in names
    assert "Sistem Ayarları" in names  # localized name


@pytest.mark.parametrize("query,expected", [
    ("youtube music", "YouTube Music for Desktop"),
    ("pear desktop", "Pear Desktop"),
    ("blender", "Blender"),
    ("sistem ayarları", "Sistem Ayarları"),
    ("system settings", "Sistem Ayarları"),
])
def test_find(query, expected):
    assert apps.CATALOG.find(query).name == expected


def test_unknown_app():
    assert apps.CATALOG.find("photoshop") is None
    assert resolve_app("notepad++") is None


def test_resolve_launches_desktop_entry_and_aliases():
    yt = resolve_app("YouTube Music")
    assert yt.cmd == ["gtk-launch", "youtube-music-for-desktop"]
    term = resolve_app("terminal")      # curated preference: Konsole over Alacritty
    assert term.label == "Konsole" and not term.sensitive


def test_system_tools_need_approval():
    reg = build_default_registry()
    spec, p = reg.validate("launch_app", {"app": "sistem ayarları"})
    assert spec.risk_for(p) == Risk.SENSITIVE
    spec, p = reg.validate("launch_app", {"app": "gparted"})
    assert spec.risk_for(p) == Risk.SENSITIVE   # pkexec / Filesystem
    spec, p = reg.validate("launch_app", {"app": "blender"})
    assert spec.risk_for(p) == Risk.SAFE


def test_intent_youtube_music():
    intent = parse_intent("Volb, YouTube Music'i aç")
    assert intent.action == "launch_app" and intent.params["app"] == "youtube music"
    assert parse_intent("Volb, YouTube'u aç").action == "open_url"       # site still wins for plain YouTube
    assert parse_intent("blenderı başlat").params["app"] == "blender"


def test_prefers_running_client(monkeypatch):
    monkeypatch.setattr(apps, "is_running", lambda app: app.name == "Pear Desktop")
    assert resolve_app("youtube music").label == "Pear Desktop"
    assert resolve_app("YouTube Music for Desktop").label == "YouTube Music for Desktop"   # explicit name wins
