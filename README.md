# YAPAY VOLB

Kişisel yapay zekâ masaüstü asistanın. **VOLB** — bol kapüşonlu hoodie giyen, havalı ve hafif gizemli bir ördek —
tamamen kodla (Qt Quick Shapes, gradyanlar, partiküller, prosedürel animasyon) çizilir; hiçbir hazır görsel/GIF kullanılmaz.

- **Arayüz:** PySide6 + Qt Quick/QML, fütüristik HUD paneli (koyu cam paneller, ince parlayan kenarlar, ikili rakamlar)
- **Beyin:** Claude Code CLI üzerinden kendi **Claude Pro** aboneliğin (ücretli API'ye asla kendiliğinden geçmez)
- **Ses:** Faster-Whisper (TR/EN), Piper TTS (yerel Türkçe), isteğe bağlı Edge TTS, bas-konuş + "Volb" uyandırma kelimesi
- **Araştırma:** Playwright Chromium ile arama → kaynak okuma → yalnızca kaynaklara dayanan, numaralı atıflı rapor
- **Bilgisayar kontrolü:** izin listesi tabanlı eylemler + riskli işlemler için onay penceresi
- **Hafıza:** SQLite (sohbet, tercihler, notlar, görevler, araştırmalar, ayarlar), isteğe bağlı ChromaDB

## Hızlı başlangıç (CachyOS / Arch)

```bash
sudo pacman -S --needed pyside6 qt6-declarative qt6-multimedia portaudio ffmpeg
uv venv --python 3.14 --system-site-packages .venv      # sistemdeki PySide6'yı kullanır
VIRTUAL_ENV=.venv uv pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python scripts/download_models.py --whisper small   # Türkçe Piper sesi + Whisper modeli
./run.sh                                                      # veya: .venv/bin/python main.py --windowed
```

**Claude Pro bağlantısı:** terminalde bir kez `claude auth login` çalıştırıp Pro hesabınla giriş yap, ardından
sağ paneldeki ⟳ düğmesine bas. Claude Code kurulu değilse uygulama kurulum talimatını gösterir:
`curl -fsSL https://claude.ai/install.sh | bash`.

Uygulama menüsüne eklemek (ve istersen girişte otomatik başlatmak) için: `scripts/install_desktop_entry.sh [--autostart]`.

**GPU'da Whisper (isteğe bağlı):** `VIRTUAL_ENV=.venv uv pip install nvidia-cublas-cu12 nvidia-cudnn-cu12` — VOLB bu
kütüphaneleri otomatik yükler; yoksa CPU (int8) kullanır.

## Kullanım

| Ne | Nasıl |
|---|---|
| Sesli komut | 🎙 düğmesini basılı tut, konuş, bırak |
| Sürekli dinleme | Alt çubuktaki "Sürekli" anahtarı veya **F2**. Sadece "Volb, …" ile başlayan cümleler işlenir |
| Yazılı komut | Alt kutuya yaz, Enter |
| Durdur | **Esc** (her şeyi), ■ Sustur (sadece konuşmayı) |
| Sayfalar | Sol menü veya **Ctrl+1…9** |

Örnekler: `Volb, Google'ı aç.` · `Volb, Blender'ı başlat.` · `Volb, bilgisayarımın RAM kullanımını göster.` ·
`Volb, bugün yapay zekâ haberlerini araştır.` · `Volb, masaüstünde Projeler adında klasör oluştur.` ·
`Volb, hatırla: en sevdiğim editör Neovim.` · `rapor dosyasını bul` · `ekran görüntüsü al` ·
`Volb, yarın saat 9'da YouTube Music'i aç.` · `10 dakika sonra bana çayı hatırlat` · `her gün 08:30'da yapay zekâ haberlerini araştır` · `Pear Desktop'ta DEEP CODING listesini çal` · `Firefox'u aç ve github'a git`

Bilinen basit komutlar yerelde (yapay zekâya gitmeden) anında çalışır; geri kalan her şey Claude'a gider. Claude bir
eylem gerekiyorsa yalnızca izinli eylemleri JSON plan olarak **önerebilir**; VOLB bunları doğrular, gerekirse onayını
ister ve kendi sabit Python kodu ile çalıştırır.

## Güvenlik modeli

- **Keyfi komut yok.** Yapay zekânın ürettiği metin asla kabuğa (shell) gitmez. Her yetenek pydantic şemalı, sabit risk
  seviyeli kayıtlı bir eylemdir (`app/computer/actions.py`). Uygulamalar yalnızca sisteme kayıtlı .desktop girdileriyle (`gtk-launch`) açılır; ayar/paket yöneticisi/disk/root araçları onay ister. Siteler izin listesinden veya http(s) adresinden açılır.
- **Onay:** hassas (ekran görüntüsü, belge okuma, klasör oluşturma), dışa açık, yıkıcı eylemler onay penceresi ister.
  Yönetici ve finansal eylemler hiç yapılmaz. Silme eylemi yoktur.
- **Claude Code araçları kapalı** (`--tools ""`); VOLB'un eylem sistemi dışında hiçbir şey yapılamaz.
- **Abonelik koruması:** `ANTHROPIC_API_KEY` vb. CLI ortamından silinir; CLI API anahtarıyla giriş yapmışsa VOLB çalışmayı
  reddeder. Parola/token saklanmaz, okunmaz.
- **Web içeriği güvenilmezdir:** kaynaklar `<kaynak>` etiketleriyle "veri" olarak işaretlenir; içlerindeki talimatlar
  uygulanmaz. Kaynak okunamazsa özet uydurulmaz, ham alıntılar gösterilir.
- Hassas dosyalar (`.ssh`, `.gnupg`, `.env`, anahtar zincirleri…) okunmaz. Tüm veriler `data/` altında, yerelde kalır;
  Hafıza sayfasından görüntülenip düzenlenebilir, JSON olarak dışa aktarılabilir ve silinebilir.

## Mimari

```
main.py                    QGuiApplication + QML motoru
app/core/                  ayarlar (pydantic), asyncio arka plan döngüsü, loglama, durum enum'u
app/ai/                    AIProvider arayüzü · ClaudeCodeCLIProvider · OllamaProvider · AnthropicAPIProvider (opt-in)
app/agents/                intent.py (TR/EN komut ayrıştırıcı) · orchestrator.py (beyin) · tasks.py (görev durumları)
app/computer/              izinli eylemler · sistem monitörü (psutil)
app/browser/               Playwright denetleyici · araştırma servisi (+ Wikipedia/SearXNG API yedeği)
app/voice/                 mikrofon/hoparlör · enerji VAD · Faster-Whisper · uyandırma kelimesi · Piper/Edge TTS
app/memory/                SQLite veritabanı · ChromaDB anlamsal hafıza (isteğe bağlı)
app/security/              risk seviyeleri ve onay politikası
app/services/              QML köprüsü (Backend QObject) · sohbet modeli
ui/main.qml                pano düzeni
ui/components/             VolbCharacter · Hoodie · DuckHead · DuckEyes · DuckBeak · ParticleSystem · VoiceVisualizer
                           HolographicPanel · RingGauge · … 
ui/pages/                  Dashboard · Chat · Research · Browser · Tasks · Memory · System · Settings
tools/                     render_gallery.py (tüm karakter durumları) · voice_selftest.py · research_selftest.py
tests/                     pytest (110 test)
```

Qt ana iş parçacığına sahiptir; tüm async iş (Claude CLI, Playwright, STT/TTS) ayrı bir asyncio döngüsünde çalışır ve
sonuçlar Qt sinyalleriyle arayüze döner. Karakter durumu (`idle/listening/thinking/speaking/working/error`) doğrudan
`backend.state` özelliğinden gelir; ağız animasyonu TTS çıkış seviyesine (`speechLevel`), dinleme dalgaları mikrofon
seviyesine (`micLevel`) bağlıdır.

## Geliştirme

```bash
.venv/bin/python -m pytest                          # testler
.venv/bin/python tools/render_gallery.py out.png    # 6 karakter durumunu tek PNG'ye çiz
.venv/bin/python tools/voice_selftest.py            # Piper → Whisper → uyandırma kelimesi → intent + mikrofon testi
.venv/bin/python tools/research_selftest.py "konu"  # gerçek web araştırması
.venv/bin/python main.py --windowed --state speaking --page 0      # belirli durumu/sayfayı aç
.venv/bin/python main.py --send "Volb, saat kaç?" --screenshot s.png
```

Ayarlar → *Animasyon önizleme* bölümünden tüm VOLB durumlarını canlı deneyebilirsin.

## Geliştirme kontrol listesi

### Faz 1 — Masaüstü uygulaması ve VOLB karakteri
- [x] Ortam incelemesi (CachyOS, Python 3.14, PySide6 6.12, RTX 4060 + Intel UHD, Wayland 1920×1080, G733 mikrofon, Claude Code 2.1.220)
- [x] Proje yapısı, venv, bağımlılıklar
- [x] Prosedürel VOLB: hoodie (gövde, kapüşon, iç gölge, kenar, ipler), kafa, gözler, gaga — ayrı bileşenler
- [x] Animasyonlar: süzülme, göz kırpma (çift kırpma dahil), bakış sıçramaları, kafa eğimi, hoodie nefesi, ip sallanması
- [x] Durumlar: dinleme (dalgalar, mikrofon tepkisi), düşünme (dönen hex sayılar, işlem halkası), konuşma (gaga senkronu, ses yayları), çalışma (holografik paneller, tarama çizgisi), hata (kırmızı, kafa karışıklığı, glitch)
- [x] Partiküller + ikili rakam akışı, holografik projektör tabanı
- [x] Pano: sol menü, merkez karakter, sağ durum paneli, alt ses/metin çubuğu, duyarlı yerleşim
- [x] Uygulama gerçekten başlatıldı ve ekran görüntüleriyle doğrulandı

### Faz 2 — Claude Code CLI
- [x] `AIProvider` arayüzü, `ClaudeCodeCLIProvider` (algılama, `auth status`, stream-json akış, `--resume` ile oturum sürekliliği)
- [x] Limit / oturum / zaman aşımı hataları, kurulum ve giriş talimatları
- [x] Ücretli API koruması (ortam temizliği, API anahtarı girişini reddetme), araçlar kapalı
- [x] Ollama ve Anthropic API (açık onaylı) sağlayıcıları
- [x] Kullanım sayfası: VOLB'un harcadığı tokenler (5 sa / bugün / 7 gün / tümü, amaç ve model dağılımı, son istekler, API eşdeğeri maliyet) + CLI'nin bildirdiği Claude Pro limit durumu ve sıfırlanma geri sayımı, isteğe bağlı küçük Haiku isteğiyle limit kontrolü
- [x] Gerçek Claude Pro hesabıyla uçtan uca deneme: akışlı sohbet, `--resume`, AI eylem planı + onay, Claude yazımı kaynaklı rapor

### Faz 3 — Ses
- [x] Faster-Whisper (CUDA → CPU yedeği), TR/EN/otomatik dil
- [x] Piper TTS (Türkçe `tr_TR-dfki-medium`), Edge TTS (isteğe bağlı), yanıtları sesli okuma
- [x] Mikrofon seçimi, bas-konuş, sürekli dinleme + enerji VAD, uyandırma kelimesi mimarisi ("Volb" + yanlış duyulma varyantları)
- [x] Gaga animasyonu gerçek ses çıkış seviyesine bağlı
- [x] Uçtan uca test: Piper "Volb, Blender'ı başlat." → Whisper birebir çözdü → intent `launch_app`
- [ ] GPU Whisper için `nvidia-cublas-cu12`/`nvidia-cudnn-cu12` kurulumu (isteğe bağlı)
- [ ] Ses tabanlı (openWakeWord) uyandırma dedektörü

### Faz 4 — Tarayıcı ve araştırma
- [x] Playwright Chromium: gezinme, çoklu sekme, içerik çıkarma, ekran görüntüsü
- [x] Arama (DuckDuckGo → Bing → Wikipedia/SearXNG API), kaynak okuma, numaralı atıflı rapor, kayıt
- [x] Web içeriği güvenilmez veri olarak işaretleniyor; yapay zekâ yoksa uydurma yerine ham alıntılar
- [x] Gerçek araştırma testi (3 gerçek kaynak okundu)

### Faz 5 — Güvenli bilgisayar kontrolü
- [x] İzin listeli eylemler: uygulama başlatma, site/klasör açma, dosya arama, belge okuma (+özet), klasör oluşturma, sistem durumu, ekran görüntüsü, saat
- [x] Risk seviyeleri + onay penceresi (3 dk zaman aşımı), yasak kategoriler, hassas dosya koruması

### Faz 6 — Hafıza ve görevler
- [x] SQLite: sohbet, tercihler, notlar, görevler, araştırmalar, ayarlar, eylem günlüğü
- [x] Hafıza sayfası: ekle / düzenle / sil / JSON dışa aktar / tüm kişisel verileri sil; sohbette "hatırla: …"
- [x] İsteğe bağlı ChromaDB anlamsal hafıza
- [x] Görev yöneticisi: Bekliyor, Planlanıyor, Çalışıyor, Onay bekliyor, Tamamlandı, Başarısız, İptal; çok adımlı planlar, ilerleme, iptal

### Faz 6b — Zamanlanmış görevler ve uygulama içi kontrol
- [x] Türkçe/İngilizce zaman ayrıştırıcı (`X dakika sonra`, `yarın 9'da`, `cuma akşam 8'de`, `12 kasım 14:00`, `her gün / hafta içi / her pazartesi / her saat`)
- [x] SQLite'ta kalıcı zamanlayıcı: hatırlatmalar (sohbet + ses + masaüstü bildirimi) ve komutlar (normal onay kurallarıyla); kapalıyken kaçırılanlar işaretlenir
- [x] Görevler sayfasında zamanlanmış görevler paneli (aç/kapat, şimdi çalıştır, sil); Claude önerirse onay gerekir
- [x] Uygulama içi kontrol (AT-SPI): öğeleri adıyla bulup tıklama/yazma, Wayland'da çalışır; Electron/Chromium uygulamaları `--force-renderer-accessibility` ile açılır
- [x] Claude adım adım ajan döngüsü (en fazla 10 adım), hedefin gerçekleştiğini görmeden bitirmez; sil/satın al/gönder vb. tıklamalar onay ister, parola alanlarına yazılmaz
- [x] Gerçek test: Pear Desktop'ta DEEP CODING listesi açılıp çalındı (MPRIS: Playing)
- [x] Ses kuyruğu: yanıtlar üst üste binmez, yeni komut eski konuşmayı keser; tek VOLB örneği kilidi
- [x] Anında medya kontrolü (MPRIS, yapay zekâsız): durdur/devam/sonraki/önceki/karışık çal/ne çalıyor, müzik ve sistem sesi
- [x] Aynı ada uyan birden fazla uygulama varsa açık olan tercih edilir (YouTube Music → çalışan Pear Desktop)
- [x] Claude çağrıları paralel güvenli: uygulama ajanı / araştırma sohbet oturumunu bozmaz
- [x] Uygulama ajanı dayanıklı: Electron öğeleri yeniden oluşturunca öğeyi adıyla tekrar bulup dener; tek adım hatası görevi düşürmez
- [x] Whisper'a kurulu uygulama adları verilir (Pear Desktop doğru yazılır), "peer/pir/PR desktop" gibi duyuşlar eşlenir

### Faz 7 — Test, optimizasyon, belgeler, paketleme
- [x] 110 pytest testi (intent, güvenlik, sahte `claude` ile CLI sağlayıcı, orkestratör onayları, hafıza, ses, araştırma)
- [x] README, AGENTS.md, .env.example, başlatıcı (`run.sh`), masaüstü girdisi betiği
- [ ] Windows'ta deneme (kod taşınabilir yazıldı: `os.startfile`, ayrık süreç bayrakları)
- [ ] PyInstaller/AppImage paketi

## Uygulama içi kontrol notları

- VOLB, KDE/GNOME'un erişilebilirlik veriyolunu (`org.a11y.Status.IsEnabled`) ilk kullanımda açar; uygulamalar
  arayüzlerini bu sayede bildirir. Kapatmak için: Sistem Ayarları → Erişilebilirlik, ya da
  `gdbus call --session --dest org.a11y.Bus --object-path /org/a11y/bus --method org.freedesktop.DBus.Properties.Set org.a11y.Status IsEnabled "<false>"`.
- Electron uygulamaları (Pear/YouTube Music, Discord, VS Code…) içeriklerini ancak `--force-renderer-accessibility` ile
  açıldıklarında gösterir. VOLB bu uygulamaları bu bayrakla başlatır; önceden açıksa yeniden başlatmak için onay ister.
- Zamanlanmış görevler VOLB açıkken çalışır. Bilgisayarın kendiliğinden uykuya geçmesini VOLB engeller
  (Ayarlar → Uyku kipini engelle: VOLB açıkken / yaklaşan görev varken / kapalı). Menüden uyutmak ve kapağı
  kapatmak yine çalışır; uykuda geçen görevler uyanınca 15 dk içindeyse çalışır, daha eskiyse “Kaçırıldı” olur. Bilgisayar açılınca VOLB'un başlaması için: `scripts/install_desktop_entry.sh --autostart`.
