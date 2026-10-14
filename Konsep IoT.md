Konsep IoT pada Modul Kustom Odoo 19: Budidaya Ikan Air Tawar Sistem RAS
1. Tujuan

RAS (Recirculating Aquaculture System) sangat bergantung pada kualitas air yang stabil. Kegagalan pompa atau aerator selama 30-60 menit saja bisa menyebabkan kematian massal. Karena itu, modul ini punya empat tujuan:

Monitoring kualitas air dan status peralatan secara real-time.
Alert dan tindakan otomatis saat parameter keluar batas.
Pencatatan produksi per batch (pakan, sampling, mortalitas, panen).
Integrasi bisnis: stok pakan, maintenance, biaya produksi (HPP), dan penjualan.
2. Arsitektur
┌─────────────────── LAPANGAN (Edge) ───────────────────┐
│ Sensor: DO, pH, suhu, ORP, TDS, turbidity, level air, │
│         flow, (amonia/nitrit: online probe atau manual)│
│ Aktuator: aerator/blower, pompa, heater, UV, feeder    │
│ Kontroler: ESP32 / PLC kecil + relay                   │
└──────────────┬────────────────────────────────────────┘
               │ MQTT (lokal, TLS)
        ┌──────▼───────┐
        │ Edge Gateway │  Mosquitto + Node-RED
        │ (mini PC/RPi)│  buffer offline, filter, agregasi
        └──────┬───────┘
               │ HTTPS (JSON-2 API / controller kustom)
        ┌──────▼───────────────────────────────┐
        │ ODOO 19 – modul `aqua_ras`           │
        │ master data, rules, alert, batch,    │
        │ maintenance, inventory, accounting   │
        └──────┬───────────────────────────────┘
               │ (opsional)
        ┌──────▼───────┐
        │ TimescaleDB/ │  data mentah time-series
        │ InfluxDB +   │  Odoo hanya simpan agregat
        │ Grafana      │
        └──────────────┘

Prinsip penting:

Kontrol kritis (aerator, pompa cadangan) dijalankan di edge, bukan menunggu Odoo. Kalau internet atau Odoo mati, sistem tetap aman.
Jangan simpan data mentah per detik di PostgreSQL Odoo. Simpan agregat (rata-rata, min, maks per 5 menit atau per jam) dan data mentah di time-series DB.
Gateway menyimpan data sementara (buffer) saat koneksi putus, lalu mengirim ulang.
3. Parameter yang dipantau

Nilai berikut hanya contoh awal untuk nila/lele. Sesuaikan dengan spesies dan rekomendasi teknisi atau penyuluh perikanan setempat.

Parameter	Kisaran umum	Metode
Oksigen terlarut (DO)	> 5 mg/L (alarm < 4)	Sensor online
Suhu	26-30 °C (nila)	Sensor online
pH	6,5-8,5	Sensor online
Amonia (TAN/NH₃)	NH₃ sebaiknya < 0,02-0,05 mg/L	Test kit/fotometer, input manual atau probe
Nitrit	< 0,1-1 mg/L	Input manual
Nitrat	< 100-150 mg/L	Input manual
Level air, flow	Sesuai desain	Sensor online
Status alat	ON/OFF, arus, jam operasi	Relay feedback, sensor arus

Parameter yang tidak ada sensor online-nya tetap dicatat lewat form pengecekan manual di Odoo (bisa dari HP), dan memakai mesin alert yang sama.

4. Desain modul aqua_ras
Struktur model
Model	Fungsi
aqua.farm	Lokasi/unit usaha
aqua.tank	Kolam/tangki: volume, spesies, status, relasi ke sistem filtrasi
aqua.system	Satu loop RAS (tank + drum filter + biofilter + sump + UV)
aqua.device	Sensor/aktuator: tipe, topic MQTT, kalibrasi terakhir, tank terkait
aqua.reading.agg	Agregat pembacaan (avg/min/max per interval)
aqua.alert.rule	Aturan: parameter, batas, durasi, severity, aksi
aqua.alert	Kejadian alarm: waktu mulai/selesai, status, acknowledged by
aqua.batch	Siklus budidaya (cohort): tebar, spesies, jumlah, bobot awal
aqua.feeding	Log pemberian pakan (manual atau dari auto feeder)
aqua.sampling	Sampling bobot rata-rata (ABW) dan panjang
aqua.mortality	Kematian harian dan penyebab
aqua.water.test	Input manual: amonia, nitrit, nitrat, alkalinitas
aqua.harvest	Panen parsial/total
Relasi ke modul standar Odoo
Inventory: pakan, probiotik, obat, dan kapur sebagai produk. Pemberian pakan membuat stock move otomatis. Benih dan hasil panen sebagai produk dengan lot.
Maintenance: alert alat (misalnya arus pompa turun, jam operasi blower mencapai batas servis) membuat maintenance request. Alat diregistrasi sebagai equipment.
Accounting/Analytic: setiap batch = satu analytic account, sehingga pakan, listrik, tenaga kerja, dan benih terakumulasi menjadi HPP per kg.
Sales: hasil panen masuk stok dan terhubung ke sales order.
Discuss/Mail: notifikasi alarm via chatter, aktivitas, atau webhook WhatsApp/Telegram.
Project/Task (opsional): SOP harian (cek manual, backwash, sampling) sebagai tugas berulang.
5. Alur kerja utama

A. Ingest data sensor

ESP32 publish ke farm1/tank3/do (nilai, timestamp).
Node-RED menerima, memvalidasi, mengagregasi (misalnya per 1-5 menit), lalu POST batch ke Odoo.
Odoo menyimpan ke aqua.reading.agg, memperbarui “nilai terakhir” di aqua.device (untuk dashboard), dan mengevaluasi aturan alert.

B. Alert bertingkat

Warning (DO < 5 selama 5 menit): notifikasi ke operator.
Critical (DO < 3,5 selama 3 menit): notifikasi ke operator dan supervisor, plus perintah menyalakan aerator cadangan (dieksekusi lewat gateway).
Eskalasi: jika belum di-acknowledge dalam X menit, naik ke level berikutnya.
Gunakan histeresis dan durasi minimum agar tidak terjadi alarm palsu.

C. Siklus batch
Tebar → pencatatan pakan harian → sampling berkala → mortalitas → panen. Sistem menghitung otomatis:

Biomassa dan ADG/SGR
FCR = total pakan / pertambahan biomassa
SR (survival rate)
Rekomendasi ration pakan (% biomassa, bergantung suhu dan ukuran ikan)

D. Pakan cerdas (tahap lanjut)
Jika DO atau suhu di bawah ambang, jadwal pakan otomatis ditunda atau dikurangi, karena nafsu makan turun dan beban amonia naik.

6. Tampilan di Odoo 19
Dashboard farm: kartu per tank dengan nilai terakhir dan indikator warna (hijau/kuning/merah), jumlah alarm aktif, dan status alat.
Grafik tren (jam/hari/minggu) per parameter. Bisa dengan komponen chart di OWL, atau embed Grafana.
Form batch: KPI (FCR, SR, biomassa, umur, estimasi panen) ditampilkan sebagai smart button dan ringkasan.
Mobile-friendly form untuk input manual cek air, pakan, dan mortalitas dari lapangan.
Laporan: performa per batch, per tank, perbandingan antar siklus, dan rekap alarm.
7. Contoh kerangka kode

Model aturan alert (disederhanakan):

python
from odoo import models, fields, api

class AquaAlertRule(models.Model):
    _name = "aqua.alert.rule"
    _description = "Aturan Alert Kualitas Air"

    name = fields.Char(required=True)
    parameter = fields.Selection([
        ("do", "Oksigen Terlarut"), ("ph", "pH"),
        ("temp", "Suhu"), ("level", "Level Air"),
    ], required=True)
    operator = fields.Selection([("lt", "<"), ("gt", ">")], required=True)
    threshold = fields.Float(required=True)
    duration_min = fields.Integer(default=5, help="Harus terpenuhi selama N menit")
    severity = fields.Selection(
        [("warning", "Warning"), ("critical", "Critical")], default="warning")
    tank_ids = fields.Many2many("aqua.tank")
    notify_user_ids = fields.Many2many("res.users")

Endpoint penerimaan data dari gateway:

python
from odoo import http
from odoo.http import request

class AquaIngest(http.Controller):

    @http.route("/aqua/ingest", type="jsonrpc", auth="public",
                methods=["POST"], csrf=False)
    def ingest(self, **payload):
        # Validasi token per gateway (jangan auth=public tanpa pengecekan!)
        gateway = request.env["aqua.gateway"].sudo()._authenticate(
            request.httprequest.headers.get("X-Gateway-Key"))
        if not gateway:
            return {"status": "unauthorized"}
        request.env["aqua.reading.agg"].sudo().ingest_batch(
            gateway, payload.get("readings", []))
        return {"status": "ok"}

Alternatifnya, gateway memakai External JSON-2 API bawaan Odoo 19 dengan API key milik user teknis. Di Odoo 19, API ini menggantikan XML-RPC/JSON-RPC lama, yang dijadwalkan dihapus pada versi berikutnya. Cek dokumentasi resmi untuk format dan batasan terbarunya, karena pada Odoo 19 tipe route json juga mengalami penyesuaian penamaan.

8. Keamanan dan keandalan
Segmentasi jaringan: perangkat IoT di VLAN terpisah, MQTT dengan TLS dan autentikasi per perangkat.
API key terpisah per gateway dengan hak akses minimum (hanya bisa menulis ke model ingest).
Hak akses Odoo: peran Operator, Supervisor, Manager (record rules per farm).
Fail-safe di edge: alarm lokal (buzzer/lampu), genset atau UPS untuk aerator dan gateway, serta watchdog yang memberi alarm jika sensor berhenti mengirim data.
Kalibrasi sensor terjadwal di modul (pH dan DO perlu kalibrasi rutin); data dari sensor yang kalibrasinya kedaluwarsa diberi penanda.
Retensi data: hapus atau arsipkan agregat berusia lebih dari N bulan lewat cron.
9. Tahapan implementasi
Fase	Cakupan
1 (MVP, ±1-2 bulan)	Master data, input manual (pakan, sampling, mortalitas, cek air), batch + KPI (FCR, SR), integrasi inventory
2	Sensor DO/suhu/pH → gateway → Odoo, dashboard, alert + notifikasi
3	Maintenance otomatis, HPP per batch, laporan lanjutan
4	Kontrol otomatis (aerator cadangan, feeder), rekomendasi pakan, analitik prediktif

Mulailah dari fase 1 dan 2 agar nilai bisnisnya terlihat cepat dan risikonya kecil.

10. Catatan penting
Ambang batas parameter di atas bersifat umum dan perlu divalidasi dengan ahli budidaya untuk spesies dan kepadatan tebar yang dipakai.
Perubahan antarversi Odoo (terutama API dan komponen frontend OWL) bisa memengaruhi kode, jadi cocokkan dengan dokumentasi Odoo 19 saat implementasi.

Kalau mau, aku bisa lanjutkan dengan salah satu dari ini: struktur folder dan __manifest__.py modul lengkap, desain ERD detail, kode MQTT/Node-RED ke Odoo, atau rumus perhitungan FCR/SR/ration pakan. Aku juga bisa menyimpan konsep ini sebagai dokumen kalau kamu butuh versi yang bisa dibagikan.
