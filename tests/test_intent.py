import pytest

from app.agents.intent import parse_intent, strip_wake_word


@pytest.mark.parametrize("text,action,key,value", [
    ("Volb, Google'ı aç.", "open_url", "url", "https://www.google.com"),
    ("volb youtube'u aç", "open_url", "url", "https://www.youtube.com"),
    ("Volb, Blender'ı başlat.", "launch_app", "app", "blender"),
    ("firefox'u çalıştır", "launch_app", "app", "firefox"),
    ("terminali aç", "launch_app", "app", "terminal"),
    ("open github", "open_url", "url", "https://github.com"),
    ("Volb, github.com/anthropics aç", "open_url", "url", "github.com/anthropics"),
    ("Volb, bugün yapay zekâ haberlerini araştır.", "research", "topic", "bugün yapay zekâ haberlerini"),
    ("research quantum computing", "research", "topic", "quantum computing"),
    ("Volb, bilgisayarımın RAM kullanımını göster.", "system_stats", "focus", "ram"),
    ("işlemci kullanımı ne kadar", "system_stats", "focus", "cpu"),
    ("indirilenler klasörünü aç", "open_directory", "path", "indirilenler"),
    ("rapor dosyasını bul", "search_files", "query", "rapor"),
])
def test_parse(text, action, key, value):
    intent = parse_intent(text)
    assert intent is not None, text
    assert intent.action == action
    assert intent.params[key] == value


def test_time_and_screenshot():
    assert parse_intent("Volb saat kaç?").action == "current_time"
    assert parse_intent("ekran görüntüsü al").action == "screenshot"


def test_create_folder_on_desktop():
    intent = parse_intent("Volb, Projeler adında bir klasör oluştur")
    assert intent.action == "create_folder"
    assert intent.params["path"].endswith("/projeler")


def test_unknown_goes_to_ai():
    assert parse_intent("Volb, bana Python'da bir decorator örneği yazar mısın?") is None
    assert parse_intent("rastgeleuygulama'yı başlat") is None   # not on the allowlist


def test_wake_word():
    assert strip_wake_word("Volb, merhaba") == (True, "merhaba")
    assert strip_wake_word("hey volb naber") == (True, "naber")
    assert strip_wake_word("merhaba") == (False, "merhaba")
