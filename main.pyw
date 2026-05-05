import pyperclip
from pynput import keyboard
import pyautogui
import tkinter as tk
from tkinter import messagebox
import time
import threading
import requests
import queue
import socket
import sys


# ============================================================
# Email Decision Engine
# Seçili e-posta metnini F8 ile analiz eder.
# Çıktı: Özet + Yapılacaklar + Öncelik + Deadline
# ============================================================


# ============================================================
# TEK UYGULAMA KONTROLÜ
# Aynı program birden fazla kez açılırsa F8 birden fazla pencere üretmesin.
# ============================================================

LOCK_SOCKET = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    LOCK_SOCKET.bind(("127.0.0.1", 65432))
except OSError:
    print("Email Decision Engine zaten çalışıyor.")
    print("Önce açık olan uygulamayı kapatın veya Görev Yöneticisi'nden pythonw.exe sürecini sonlandırın.")
    sys.exit()


# --- OLLAMA AYARLARI ---
OLLAMA_TAGS_URL = "http://localhost:11434/api/tags"
OLLAMA_GENERATE_URL = "http://localhost:11434/api/generate"

TEXT_MODEL_CANDIDATES = [
    "gemma3:1b",
    "llama3.2:latest",
    "llama3.1:latest",
    "mistral:latest",
]

# F8 kısayolu
KISAYOL_METIN = keyboard.Key.f8

root = None
gui_queue = queue.Queue()
kisayol_basildi = False
analiz_devam_ediyor = False


# --- MAIL ANALİZ PROMPT'U ---
MAIL_ANALIZ_PROMPT = """
Sen bir e-posta görev analiz asistanısın.

Görevin:
Kullanıcının seçtiği e-posta metnini analiz etmek, kısa özet çıkarmak, yapılacak işleri belirlemek, her iş için öncelik ve deadline bilgisini yazmaktır.

ÇOK ÖNEMLİ:
Cevabın SADECE aşağıdaki formatta olmalı.
Formatı değiştirme.
Ek açıklama yazma.
Kuralları cevaba ekleme.
Markdown kullanma.
Madde işaretlerini farklılaştırma.

ÇIKTI FORMATI:

Özet:
[E-postadaki ana isteği 1 veya 2 kısa cümleyle özetle. Daha uzun olmasın.]

Yapılacaklar:

1. Görev: [Birinci yapılacak işi kısa ve net yaz.]
   Öncelik: [HIGH / MEDIUM / LOW]
   Deadline: [Mailde geçen tarih veya zaman ifadesi. Yoksa Belirtilmemiş yaz.]

2. Görev: [İkinci yapılacak işi kısa ve net yaz.]
   Öncelik: [HIGH / MEDIUM / LOW]
   Deadline: [Mailde geçen tarih veya zaman ifadesi. Yoksa Belirtilmemiş yaz.]

3. Görev: [Üçüncü yapılacak işi kısa ve net yaz.]
   Öncelik: [HIGH / MEDIUM / LOW]
   Deadline: [Mailde geçen tarih veya zaman ifadesi. Yoksa Belirtilmemiş yaz.]

FORMAT KURALLARI:
- Her görev numarası sadece "1. Görev:", "2. Görev:", "3. Görev:" şeklinde başlamalı.
- "Öncelik" ve "Deadline" aynı görevin altında girintili yazılmalı.
- "Öncelik" satırını ayrı numara olarak yazma.
- "Deadline" satırını ayrı numara olarak yazma.
- Cevapta "ÇIKTI FORMATI", "FORMAT KURALLARI" veya "Kurallar" başlıklarını yazma.
- Görev uydurma.
- Mailde açıkça istenmeyen işi yazma.
- Öncelik değeri sadece HIGH, MEDIUM veya LOW olabilir.
- HIGH yalnızca mailde "acil", "kritik", "bugün", "hemen", "kesinti", "güvenlik riski" veya "bloke" gibi açık aciliyet/etki ifadesi varsa kullanılmalı.
- MEDIUM tarih verilmiş kontrol, analiz, düzenleme, güncelleme, tamamlama, son kontrol, durum paylaşımı ve takip işleri için kullanılmalı.
- LOW yalnızca bilgilendirme veya düşük etkili notlar için kullanılmalı.
- "Öncelikli", "önemli", "rica ederim" veya sadece tarih/deadline geçmesi HIGH sebebi değildir.
- Yakın tarihli ancak kritik olmayan işler MEDIUM olmalı.
- Bilgilendirme amaçlı işler LOW olmalı.
- Bugün, yarın, Cuma günü, hafta sonu gibi ifadeleri Deadline alanına aynen yaz.
- Tarih yoksa Deadline: Belirtilmemiş yaz.
- Çıktı Türkçe olsun.

DOĞRU ÖRNEK:

Özet:
E-postada sistem hatalarının giderilmesi ve performans analizinin hazırlanması istenmektedir.

Yapılacaklar:

1. Görev: Sistem hatasını incele ve çöz.
   Öncelik: HIGH
   Deadline: Bugün içerisinde

2. Görev: Performans iyileştirme analizi hazırla.
   Öncelik: MEDIUM
   Deadline: Belirtilmemiş

3. Görev: Analiz sonuçlarını paylaş.
   Öncelik: MEDIUM
   Deadline: Yarına kadar
"""

def get_available_text_model():
    """
    Ollama üzerinde kurulu modelleri kontrol eder.
    TEXT_MODEL_CANDIDATES içinden ilk bulunan modeli döndürür.
    """
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)

        if response.status_code != 200:
            return TEXT_MODEL_CANDIDATES[0]

        data = response.json()
        models = data.get("models", [])

        installed_models = []

        for model in models:
            name = model.get("name", "")
            if name:
                installed_models.append(name)

        installed_lower_map = {
            model_name.lower(): model_name
            for model_name in installed_models
        }

        for candidate in TEXT_MODEL_CANDIDATES:
            candidate_lower = candidate.lower()

            # Tam eşleşme
            if candidate_lower in installed_lower_map:
                return installed_lower_map[candidate_lower]

            # Tag olmadan model adı eşleşmesi
            candidate_base = candidate_lower.split(":")[0]

            for installed_lower, original_name in installed_lower_map.items():
                installed_base = installed_lower.split(":")[0]

                if installed_base == candidate_base:
                    return original_name

        # Adaylardan hiçbiri yoksa kurulu ilk modeli kullan
        if installed_models:
            return installed_models[0]

    except Exception:
        pass

    return TEXT_MODEL_CANDIDATES[0]


def ollama_cevap_al(prompt):
    """
    Ollama API'ye prompt gönderir ve cevabı döndürür.
    """
    try:
        aktif_model = get_available_text_model()

        payload = {
            "model": aktif_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
            },
        }

        response = requests.post(
            OLLAMA_GENERATE_URL,
            json=payload,
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            return result.get("response", "").strip()

        hata = (
            "Ollama API hatası oluştu.\n\n"
            f"HTTP Durum Kodu: {response.status_code}\n"
            f"Kullanılan Model: {aktif_model}\n\n"
            f"Detay:\n{response.text}"
        )

        print(hata)
        gui_queue.put((messagebox.showerror, ("API Hatası", hata)))
        return None

    except requests.exceptions.ConnectionError:
        hata = (
            "Ollama servisine bağlanılamadı.\n\n"
            "Lütfen Ollama'nın çalıştığından emin olun.\n"
            "Varsayılan adres: http://localhost:11434\n\n"
            "Kontrol için CMD'de şunu çalıştırabilirsin:\n"
            "ollama list"
        )

        print(hata)
        gui_queue.put((messagebox.showerror, ("Bağlantı Hatası", hata)))
        return None

    except requests.exceptions.Timeout:
        hata = (
            "Model cevap verirken zaman aşımına uğradı.\n\n"
            "Daha kısa bir mail metni seçerek tekrar deneyebilirsin."
        )

        print(hata)
        gui_queue.put((messagebox.showerror, ("Zaman Aşımı", hata)))
        return None

    except Exception as e:
        hata = f"Beklenmeyen hata oluştu:\n\n{e}"
        print(hata)
        gui_queue.put((messagebox.showerror, ("Hata", hata)))
        return None


def strip_code_fence(text):
    """
    Model yanlışlıkla ``` gibi kod bloğu işaretleri döndürürse temizler.
    """
    if not text:
        return text

    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines:
            lines = lines[1:]

        while lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

    return cleaned


def temiz_sonuc(sonuc):
    """
    Model bazen prompt kurallarını cevaba ekleyebilir.
    Kurallar bölümü veya gereksiz prompt tekrarları varsa temizler.
    """
    if not sonuc:
        return sonuc

    sonuc = strip_code_fence(sonuc).strip()

    kesme_kelimeleri = [
        "\nKurallar:",
        "\nKURALLAR:",
        "\nKurallar",
        "\nKURALLAR",
        "\nÇIKTI FORMATI:",
        "\nÇıktı Formatı:",
    ]

    for kelime in kesme_kelimeleri:
        if kelime in sonuc:
            sonuc = sonuc.split(kelime)[0].strip()

    return sonuc


def secili_metni_kopyala(max_deneme=5):
    """
    Kullanıcının seçtiği metni Ctrl+C ile panoya alır.
    """
    sentinel = f"__MAIL_TASK_ASSISTANT_EMPTY_CLIPBOARD_{time.time_ns()}__"

    try:
        pyperclip.copy(sentinel)
    except Exception:
        pass

    for _ in range(max_deneme):
        pyautogui.hotkey("ctrl", "c")
        time.sleep(0.2)

        try:
            metin = pyperclip.paste()
        except Exception:
            metin = ""

        if metin and metin.strip() and metin != sentinel:
            return metin.strip()

    return ""


def sonuc_penceresi_goster(baslik, icerik):
    """
    Analiz sonucunu ayrı pencerede gösterir.
    """
    pencere = tk.Toplevel(root)
    pencere.title(baslik)
    pencere.geometry("850x600")
    pencere.minsize(600, 400)
    pencere.attributes("-topmost", True)

    ana_frame = tk.Frame(pencere, bg="#1f1f1f")
    ana_frame.pack(fill="both", expand=True, padx=10, pady=10)

    baslik_label = tk.Label(
        ana_frame,
        text=baslik,
        bg="#1f1f1f",
        fg="white",
        font=("Segoe UI", 13, "bold"),
        anchor="w"
    )
    baslik_label.pack(fill="x", pady=(0, 8))

    metin_frame = tk.Frame(ana_frame, bg="#1f1f1f")
    metin_frame.pack(fill="both", expand=True)

    text_alani = tk.Text(
        metin_frame,
        wrap="word",
        bg="#ffffff",
        fg="#111111",
        insertbackground="#111111",
        font=("Consolas", 10),
        padx=14,
        pady=14
    )

    kaydirma = tk.Scrollbar(metin_frame, command=text_alani.yview)
    text_alani.configure(yscrollcommand=kaydirma.set)

    text_alani.pack(side="left", fill="both", expand=True)
    kaydirma.pack(side="right", fill="y")

    text_alani.insert("1.0", icerik)
    text_alani.config(state="disabled")

    buton_frame = tk.Frame(ana_frame, bg="#1f1f1f")
    buton_frame.pack(fill="x", pady=(10, 0))

    def panoya_kopyala():
        pyperclip.copy(icerik)
        messagebox.showinfo("Kopyalandı", "Sonuç panoya kopyalandı.")

    kopyala_buton = tk.Button(
        buton_frame,
        text="Panoya Kopyala",
        command=panoya_kopyala,
        bg="#3d3d3d",
        fg="white",
        activebackground="#505050",
        activeforeground="white",
        relief="flat",
        padx=14,
        pady=7
    )
    kopyala_buton.pack(side="left")

    kapat_buton = tk.Button(
        buton_frame,
        text="Kapat",
        command=pencere.destroy,
        bg="#3d3d3d",
        fg="white",
        activebackground="#505050",
        activeforeground="white",
        relief="flat",
        padx=14,
        pady=7
    )
    kapat_buton.pack(side="right")

    pencere.focus_force()
    pencere.lift()


def islemi_yap(secili_metin):
    """
    Seçili mail metnini analiz eder.
    """
    global analiz_devam_ediyor

    try:
        full_prompt = f"""
{MAIL_ANALIZ_PROMPT}

Analiz edilecek e-posta metni:

{secili_metin}
"""

        print("=" * 60)
        print("Mail analizi başlatıldı.")
        print("Mail metni analiz ediliyor...")
        print("=" * 60)

        sonuc = ollama_cevap_al(full_prompt)

        if not sonuc:
            print("Sonuç alınamadı.")
            return

        sonuc = temiz_sonuc(sonuc)

        gui_queue.put((sonuc_penceresi_goster, ("Mailden Yapılacaklar", sonuc)))

        print("Analiz tamamlandı.")
        print("=" * 60)

    finally:
        analiz_devam_ediyor = False


def mail_analizini_baslat():
    """
    F8 basıldığında seçili mail metnini alır ve direkt analiz başlatır.
    Menü göstermez.
    """
    global analiz_devam_ediyor

    if analiz_devam_ediyor:
        gui_queue.put(
            (
                messagebox.showinfo,
                (
                    "Analiz Devam Ediyor",
                    "Mevcut analiz tamamlanmadan yeni analiz başlatılamaz.",
                ),
            )
        )
        return

    secili_metin = secili_metni_kopyala()

    if not secili_metin.strip():
        gui_queue.put(
            (
                messagebox.showwarning,
                (
                    "Seçim Bulunamadı",
                    "Lütfen önce bir mail metni seçin, ardından F8 tuşuna basın.",
                ),
            )
        )
        return

    analiz_devam_ediyor = True

    threading.Thread(
        target=islemi_yap,
        args=(secili_metin,),
        daemon=True
    ).start()


def process_queue():
    """
    Tkinter işlemlerini ana thread üzerinde çalıştırır.
    """
    try:
        while True:
            try:
                func, args = gui_queue.get_nowait()
            except queue.Empty:
                break

            func(*args)

    finally:
        if root:
            root.after(100, process_queue)


def on_press(key):
    """
    F8 basıldığında çalışır.
    """
    global kisayol_basildi

    try:
        if key == KISAYOL_METIN and not kisayol_basildi:
            kisayol_basildi = True
            gui_queue.put((mail_analizini_baslat, ()))
    except AttributeError:
        pass


def on_release(key):
    """
    F8 bırakıldığında tekrar basılabilir hale getirir.
    """
    global kisayol_basildi

    try:
        if key == KISAYOL_METIN:
            kisayol_basildi = False
    except AttributeError:
        pass


def ollama_baglanti_kontrol():
    """
    Program açılırken Ollama bağlantısını kontrol eder.
    """
    try:
        response = requests.get(OLLAMA_TAGS_URL, timeout=5)

        if response.status_code == 200:
            aktif_model = get_available_text_model()
            print("Ollama bağlantısı başarılı.")
            print(f"Kullanılacak model: {aktif_model}")
            return True

        print("Ollama çalışıyor gibi görünüyor ancak model listesi alınamadı.")
        return False

    except Exception:
        print("Ollama bağlantısı kurulamadı.")
        print("Ollama açık değilse uygulama model cevabı üretemez.")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("EMAIL DECISION ENGINE")
    print("=" * 60)
    print("Kullanım:")
    print("1. Bir mail metni seç.")
    print("2. F8 tuşuna bas.")
    print("3. Analiz sonucu otomatik olarak pencerede gösterilir.")
    print("=" * 60)

    ollama_baglanti_kontrol()

    listener = keyboard.Listener(
        on_press=on_press,
        on_release=on_release
    )
    listener.start()

    root = tk.Tk()
    root.withdraw()
    root.after(100, process_queue)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("Program kapatılıyor...")