# Aqua RAS untuk Odoo 19

Isi paket:
```
aqua_ras/   modul Odoo 19 (taruh di folder addons)
edge/       docker-compose, Mosquitto, flow Node-RED, firmware ESP32
docs/       ERD.md, RUMUS.md, README.md
```

## 1. Install modul
1. Salin `aqua_ras/` ke direktori addons Odoo, tambahkan ke `addons_path`.
2. Restart Odoo, aktifkan Developer Mode, Apps -> Update Apps List, install **Aqua RAS**.
3. Beri user grup *Aqua RAS / Operator / Supervisor / Manager* (Settings -> Users).
4. Jalankan test: `odoo -d DB -i aqua_ras --test-enable --stop-after-init`.

## 2. Setup awal di Odoo
1. **Farm** -> buat farm, tangki, dan loop sistem RAS.
2. **Gateway** -> buat gateway, klik **Generate API Key** (key tampil sekali, simpan).
3. **Sensor/Aktuator** -> daftarkan tiap sensor: kode, parameter, tangki, gateway, **MQTT topic**
   (mis. `farm1/tank3/do`), tanggal kalibrasi. Isi *equipment* bila ingin maintenance request otomatis.
4. **Aturan Alert** -> contoh:
   - DO < 5, 5 menit, Warning
   - DO < 3,5, 3 menit, Critical, eskalasi 10 menit, notifikasi operator + supervisor
   - Suhu > 32, 10 menit, Warning
   - NH3 > 0,05 (dari uji manual), Warning
5. Produk: buat produk pakan (UoM kg) dan produk hasil panen; stok awal pakan lewat Inventory.
6. (Opsional) Telegram: Settings -> Technical -> System Parameters, buat
   `aqua_ras.telegram_bot_token` dan `aqua_ras.telegram_chat_id`.
7. Retensi data agregat: `aqua_ras.retention_months` (default 12).

## 3. Setup edge
```bash
cd edge
docker run --rm -v $PWD/mosquitto:/c eclipse-mosquitto:2 sh -c \
  "touch /c/passwd && mosquitto_passwd -b /c/passwd nodered PASS1 && mosquitto_passwd -b /c/passwd esp_tank3 PASS2"
# edit docker-compose.yml: ODOO_URL dan ODOO_KEY
docker compose up -d
```
Buka Node-RED `http://host:1880` -> menu Import -> tempel `nodered/flow.json`.
Di node *Mosquitto lokal* isi username `nodered` dan password. Deploy.
Flash `esp32/ras_node.ino` (sesuaikan WiFi, kredensial MQTT, dan kalibrasi DO).

Antrian offline disimpan di memori flow. Agar bertahan setelah restart, aktifkan
`contextStorage` tipe file di `settings.js` Node-RED dan gunakan `flow.get('queue','file')`.

## 4. Uji koneksi tanpa hardware
```bash
curl -X POST https://ODOO/aqua/ingest \
  -H "Content-Type: application/json" -H "X-Gateway-Key: KEY_ANDA" \
  -d '{"readings":[{"topic":"farm1/tank3/do","ts":"2026-10-14 03:00:00","avg":3.1,"min":3.0,"max":3.2,"n":6}]}'
```
Respons sukses: `{"status":"ok","created":1,"duplicates":0,"unknown_topics":[]}`.
Jika Odoo memakai banyak database, set `dbfilter` atau tambahkan `?db=NAMA_DB` pada URL.

## 5. Alur harian operator
Pakan (kolom Pakan di batch atau menu Pakan) -> Mortalitas -> Sampling tiap 1-2 minggu -> Uji air manual
(amonia/nitrit) -> pantau kanban Tangki (hijau/oranye/merah) -> tangani alarm (Acknowledge).
Form batch menampilkan rekomendasi pakan hari ini, FCR, SR, ADG, SGR, biaya dan HPP/kg.

## 6. Hal yang perlu diverifikasi saat instalasi di Odoo 19
Modul ditulis mengikuti konvensi Odoo 18/19 (`<list>`, `models.Constraint`, `<chatter/>`, `invisible="..."`),
tetapi belum diuji pada instance Anda. Periksa terutama:
- Grup keamanan: pada Odoo 19 struktur kategori grup berubah; grup di `security.xml` sengaja dibuat sederhana.
  Tambahkan user admin ke grup Manager secara manual.
- Field `stock.move` (`quantity`, `picked`) dan `account.analytic.plan` sesuai build Odoo 19 Anda.
- Cron `ir.cron` dan atribut kanban `highlight_color`.
Bila ada error saat install, kirim log-nya dan akan mudah disesuaikan.

## 7. Pengembangan lanjutan
- Dashboard OWL dengan grafik tren interaktif (atau embed Grafana).
- Perintah aktuator dari Odoo ke gateway (topic `farm1/<tank>/cmd/...`) dengan konfirmasi dan audit log.
- Auto-feeder: gateway mengirim log pakan ke model `aqua.feeding` (source = auto).
- Record rule per farm, laporan perbandingan antar siklus, prediksi tanggal panen.
