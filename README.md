<h1 align="center">🚀 Email Decision Engine</h1>

<h3 align="center">
Seçilen e-posta metnini F8 kısayolu ile analiz eden yapay zeka destekli görev çıkarım sistemi
</h3>

<p align="center">
  <b>Özet Çıkarma</b> •
  <b>Görev Analizi</b> •
  <b>Önceliklendirme</b> •
  <b>Deadline Tespiti</b>
</p>

<p align="center">
  Local AI: Ollama
</p>

---

<p align="center">
  <a href="https://github.com/denvercoder1/readme-typing-svg">
    <img src="https://readme-typing-svg.herokuapp.com?font=Fira+Code&size=34&pause=1000&color=9D174D&center=true&vCenter=true&width=950&height=80&lines=Developed+by+Havvanur+Büşra+SAYIN;Welcome+to+Email+Decision+Engine" alt="Typing SVG" />
  </a>
</p>

## 🎯 Proje Amacı

Yoğun iş akışlarında e-postalar çoğu zaman uzun, dağınık ve takip edilmesi zor bilgiler içerir.  
Bu durum, yapılacak işlerin kaçırılmasına, önceliklerin net belirlenememesine ve teslim tarihlerinin gözden kaçmasına neden olabilir.

**Email Decision Engine**, seçilen bir e-posta metnini yapay zeka desteğiyle analiz ederek kullanıcıya daha düzenli ve aksiyon odaklı bir çıktı sunmak amacıyla geliştirilmiştir.

Uygulama, kullanıcı tarafından seçilen e-posta içeriğini **F8 kısayolu** ile doğrudan analiz eder ve aşağıdaki bilgileri çıkarır:

- E-postanın kısa özeti
- Yapılması gereken görevler
- Görevlerin öncelik seviyesi
- Her görev için deadline bilgisi
- Daha hızlı aksiyon almayı sağlayan düzenli çıktı yapısı

---

## ⚡ Özellikler

- ✉️ Seçili e-posta metnini analiz etme
- ⌨️ F8 kısayolu ile doğrudan çalışma
- 🧠 Local AI desteği ile özet çıkarma
- 📋 Yapılacaklar listesi oluşturma
- 🔥 Önceliklendirme: `HIGH / MEDIUM / LOW`
- ⏱ Deadline tespiti
- 🪟 Sonucu masaüstü penceresinde gösterme
- 📋 Analiz sonucunu panoya kopyalama
- 💻 Ollama ile local model kullanımı

---

## 🧩 Sistem Mimarisi

```mermaid
graph LR
    A["Kullanıcı e-posta metnini seçer"] --> B["F8 kısayoluna basılır"]
    B --> C["Seçili metin panoya alınır"]
    C --> D["Ollama Local AI Modeli"]
    D --> E["Özet çıkarımı"]
    D --> F["Görev analizi"]
    D --> G["Öncelik ve deadline tespiti"]
    E --> H["Sonuç penceresi"]
    F --> H
    G --> H