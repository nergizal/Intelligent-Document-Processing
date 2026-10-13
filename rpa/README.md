# RPA Modülü (UiPath)

Bu klasör, UiPath Studio ile geliştirilecek e-posta izleme / ek indirme /
AI servis entegrasyon robotunun proje köküdür.

## Klasör Yapısı

```
rpa/
├── Data/
│   ├── Input/     -> İndirilen PDF ekleri (işlenmeyi bekleyen)
│   └── Output/     -> İşlenmiş / arşivlenmiş belgeler
├── Workflows/       -> .xaml iş akışı dosyaları (UiPath Studio'dan eklenecek)
├── Config.csv        -> Config.xlsx için kaynak veri (bkz. aşağıda)
└── mock_ai_response.json -> Geliştirme/test için örnek AI servis yanıtı
```

## Config.xlsx Hakkında Not

Bu depo düz metin dosyalarından oluştuğu için ikili (binary) bir `.xlsx`
dosyası doğrudan eklenmemiştir. Bunun yerine [Config.csv](Config.csv)
dosyası, UiPath REFramework konvansiyonundaki **Settings** sayfasının
içeriğini temsil eder.

Kurulum adımı:
1. `Config.csv` dosyasını Excel ile açın.
2. "Farklı Kaydet" ile `Config.xlsx` olarak, sayfa adını **Settings**
   yapacak şekilde kaydedin.
3. Gerekiyorsa REFramework konvansiyonuna uygun **Constants** ve
   **Assets** sayfalarını ekleyin.
4. `mailUsername`, `mailPassword` gibi gizli değerleri doğrudan Excel'e
   yazmak yerine UiPath Orchestrator **Assets/Credentials** üzerinden
   yönetin.

## mock_ai_response.json

RPA geliştiricisinin, AI servisi henüz ayakta değilken/yerel testlerde
`POST /predict` çağrısının dönebileceği örnek bir yanıtı taklit etmek
için kullanabileceği sabit veridir (bkz.
[docs/API_CONTRACT.md](../docs/API_CONTRACT.md)).

## Planlanan İş Akışları (Workflows/)

| Workflow (öneri)              | Sorumluluk                                              |
|--------------------------------|-----------------------------------------------------------|
| `Main.xaml`                     | REFramework giriş noktası, init/process/end orkestrasyonu |
| `GetMailAttachments.xaml`      | IMAP/Outlook Mail'den yeni PDF eklerini indirir             |
| `CallAiPredictionService.xaml` | `Config.xlsx` içindeki `aiServicePredictUrl`'e HTTP isteği atar |
| `LogExecutionToBackend.xaml`   | `backendLogsUrl` adresine `automation_logs` kaydı gönderir |
