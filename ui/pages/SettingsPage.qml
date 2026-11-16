import QtQuick
import QtQuick.Layouts
import QtQuick.Controls.Basic
import "../components"

Flickable {
    id: root
    contentHeight: col.implicitHeight + 20
    clip: true
    ScrollBar.vertical: ScrollBar { width: 6 }
    readonly property var s: backend.settings

    function micNames() { return backend.micDevices.map(d => d.name) }
    function micIndexes() { return backend.micDevices.map(d => d.index) }

    ColumnLayout {
        id: col
        width: root.width - 12
        spacing: 12

        // ---------------------------------------------------------------- AI
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: ai.implicitHeight + 58
            title: "Yapay Zekâ Motoru"
            ColumnLayout {
                id: ai
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 14
                SettingRow {
                    label: "Sağlayıcı"
                    description: "Claude Code CLI, Claude Pro aboneliğini kullanır. VOLB hiçbir zaman kendiliğinden ücretli API'ye geçmez."
                    HudCombo {
                        values: ["claude_cli", "ollama", "anthropic_api"]
                        labels: ["Claude Code (Pro aboneliği)", "Ollama (yerel)", "Anthropic API (ücretli)"]
                        current: root.s.ai_provider
                        implicitWidth: 260
                        onPicked: (v) => backend.setSetting("ai_provider", v)
                    }
                }
                SettingRow {
                    label: "Claude modeli"
                    description: "Boş bırakılırsa Claude Code varsayılanı kullanılır (örn. sonnet, opus)."
                    HudField { implicitWidth: 260; text: root.s.claude_model || ""; placeholderText: "varsayılan"; onEditingFinished: backend.setSetting("claude_model", text) }
                }
                SettingRow {
                    label: "Ollama modeli"
                    visible: root.s.ai_provider === "ollama"
                    HudField { implicitWidth: 260; text: root.s.ollama_model || ""; onEditingFinished: backend.setSetting("ollama_model", text) }
                }
                SettingRow {
                    label: "Ücretli API'ye izin ver"
                    description: "Sadece 'Anthropic API' sağlayıcısını seçersen kullanılır ve Claude Pro'dan ayrı faturalandırılır."
                    HudSwitch { checked: !!root.s.allow_paid_api; accent: Theme.amber; onToggled: (v) => backend.setSetting("allow_paid_api", v) }
                }
                RowLayout {
                    spacing: 10
                    Rectangle { width: 10; height: 10; radius: 5; color: backend.claudeConnected ? Theme.green : Theme.amber }
                    Text { text: backend.claudeStatus + (backend.claudeDetail ? "  —  " + backend.claudeDetail : ""); color: Theme.text; font.family: Theme.font; font.pixelSize: 13
                           Layout.fillWidth: true; wrapMode: Text.WordWrap }
                    HudButton { text: "Bağlantıyı yenile"; icon: "⟳"; onClicked: backend.refreshClaude() }
                }
                TextEdit {
                    visible: backend.claudeHint.length > 0
                    Layout.fillWidth: true
                    text: backend.claudeHint
                    readOnly: true; selectByMouse: true; wrapMode: Text.WordWrap
                    color: Theme.amber; font.family: Theme.mono; font.pixelSize: 12
                }
            }
        }

        // ---------------------------------------------------------------- Voice
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: voice.implicitHeight + 58
            title: "Ses"
            tag: backend.sttStatus + "  •  TTS: " + backend.ttsStatus
            ColumnLayout {
                id: voice
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 14
                SettingRow {
                    label: "Konuşma dili"
                    description: "Whisper tanıma dili. 'Otomatik' Türkçe ve İngilizceyi kendisi algılar."
                    HudCombo { values: ["tr", "en", "auto"]; labels: ["Türkçe", "English", "Otomatik"]; current: root.s.language; onPicked: (v) => backend.setSetting("language", v) }
                }
                SettingRow {
                    label: "Uyandırma kelimesi"
                    description: "Sürekli dinleme modunda komutlar bu kelimeyle başlamalı."
                    HudField { implicitWidth: 220; text: root.s.wake_word || "volb"; onEditingFinished: backend.setSetting("wake_word", text) }
                }
                SettingRow {
                    label: "Mikrofon"
                    HudCombo { implicitWidth: 300; values: root.micIndexes(); labels: root.micNames(); current: root.s.mic_device; onPicked: (v) => backend.setSetting("mic_device", v) }
                }
                SettingRow {
                    label: "Sürekli dinleme"
                    description: "Mikrofon açık kalır; sadece '" + (root.s.wake_word || "volb") + "' ile başlayan cümleler komut olarak işlenir. (F2)"
                    HudSwitch { checked: backend.continuous; onToggled: (v) => { backend.setContinuous(v); backend.setSetting("continuous_listening", v) } }
                }
                SettingRow {
                    label: "Whisper modeli"
                    description: "Büyük modeller daha doğru ama daha yavaş. İlk kullanımda indirilir."
                    HudCombo { values: ["tiny", "base", "small", "medium", "large-v3", "turbo"]; current: root.s.stt_model; onPicked: (v) => backend.setSetting("stt_model", v) }
                }
                SettingRow {
                    label: "Whisper cihazı"
                    HudCombo { values: ["auto", "cuda", "cpu"]; labels: ["Otomatik (GPU varsa)", "CUDA (NVIDIA)", "CPU"]; current: root.s.stt_device; onPicked: (v) => backend.setSetting("stt_device", v) }
                }
                SettingRow {
                    label: "Seslendirme motoru"
                    description: "Piper tamamen yereldir. Edge TTS metni Microsoft sunucularına gönderir."
                    HudCombo { values: ["piper", "edge", "none"]; labels: ["Piper (yerel)", "Edge TTS (çevrimiçi)", "Kapalı"]; current: root.s.tts_engine; onPicked: (v) => backend.setSetting("tts_engine", v) }
                }
                SettingRow {
                    label: "Edge TTS'e izin ver"
                    HudSwitch { checked: !!root.s.allow_edge_tts; onToggled: (v) => backend.setSetting("allow_edge_tts", v) }
                }
                SettingRow {
                    label: "Piper sesi"
                    description: "models/piper/<ad>.onnx — indirmek için: python scripts/download_models.py"
                    HudField { implicitWidth: 260; text: root.s.piper_voice || ""; onEditingFinished: backend.setSetting("piper_voice", text) }
                }
                SettingRow {
                    label: "Edge sesi"
                    HudCombo { values: ["tr-TR-AhmetNeural", "tr-TR-EmelNeural", "en-US-GuyNeural", "en-US-AriaNeural"]; current: root.s.edge_voice; implicitWidth: 260
                               onPicked: (v) => backend.setSetting("edge_voice", v) }
                }
                SettingRow {
                    label: "Yanıtları sesli oku"
                    HudSwitch { checked: !!root.s.speak_responses; onToggled: (v) => backend.setSetting("speak_responses", v) }
                }
            }
        }

        // ---------------------------------------------------------------- Browser & memory
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: other.implicitHeight + 58
            title: "Tarayıcı ve Hafıza"
            ColumnLayout {
                id: other
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 14
                SettingRow {
                    label: "Görünmez tarayıcı (headless)"
                    description: "Kapalıyken VOLB'un kullandığı Chromium penceresini görebilirsin."
                    HudSwitch { checked: !!root.s.browser_headless; onToggled: (v) => backend.setSetting("browser_headless", v) }
                }
                SettingRow {
                    label: "Uyku kipini engelle"
                    description: "Zamanlanmış görevler kaçmasın diye bilgisayarın KENDİLİĞİNDEN uykuya geçmesini engeller. Menüden uyutmak ve kapağı kapatmak yine çalışır; VOLB kapanınca engel kalkar."
                        + (backend.sleepInhibited ? "  ● Şu an etkin." : "")
                    HudCombo {
                        values: ["always", "schedules", "off"]
                        labels: ["VOLB açıkken", "Yaklaşan görev varken", "Kapalı"]
                        current: root.s.sleep_inhibit
                        implicitWidth: 240
                        onPicked: (v) => backend.setSetting("sleep_inhibit", v)
                    }
                }
                SettingRow {
                    label: "Anlamsal hafıza (ChromaDB)"
                    description: "İsteğe bağlı: pip install chromadb. Değişiklik yeniden başlatınca geçerli olur."
                    HudSwitch { checked: !!root.s.semantic_memory; onToggled: (v) => backend.setSetting("semantic_memory", v) }
                }
            }
        }

        // ---------------------------------------------------------------- Animation preview
        HolographicPanel {
            Layout.fillWidth: true
            Layout.preferredHeight: 112
            title: "Animasyon önizleme"
            tag: "VOLB durumlarını test et"
            Flow {
                anchors.left: parent.left; anchors.right: parent.right
                spacing: 8
                Repeater {
                    model: ["idle", "listening", "thinking", "speaking", "working", "error"]
                    HudButton { text: Theme.stateLabel(modelData); accent: Theme.stateColor(modelData); onClicked: backend.previewState(modelData) }
                }
                HudButton { text: "Otomatik"; primary: true; onClicked: backend.previewState("") }
            }
        }

        Text {
            Layout.fillWidth: true
            horizontalAlignment: Text.AlignHCenter
            text: "YAPAY VOLB v" + backend.appVersion + "  •  PySide6 + Qt Quick  •  veriler yalnızca bu bilgisayarda (data/)"
            color: Theme.dim; font.family: Theme.mono; font.pixelSize: 11
        }
    }
}
