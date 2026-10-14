# Contoh Penerapan IoT dengan Odoo

Odoo punya modul IoT resmi yang memakai perangkat bernama IoT Box (Raspberry Pi) atau Windows Virtual IoT. Perangkat ini menjadi jembatan antara hardware di lapangan dan database Odoo. Selain itu, Odoo juga bisa diintegrasikan dengan sensor buatan sendiri (ESP32, Arduino, dll.) lewat API.

1. Penerapan bawaan Odoo (via IoT Box)

Point of Sale (POS)

Printer struk thermal, cash drawer, dan barcode scanner terhubung otomatis ke POS.
Timbangan digital untuk produk curah, sehingga berat langsung masuk ke baris transaksi.
Customer display untuk menampilkan pesanan ke pelanggan.

Manufaktur (MRP)

Work order di shop floor bisa menerima data dari alat ukur, seperti caliper atau micrometer digital, untuk quality control.
Pedal atau tombol fisik untuk pindah step atau menyelesaikan operasi tanpa menyentuh layar.
Kamera untuk mengambil foto bukti pada quality check.

Gudang (Inventory)

Timbangan untuk mencatat berat paket saat packing dan shipping.
Printer label otomatis (barcode, lot/serial number, label pengiriman).

Absensi

Kiosk dengan badge reader atau RFID untuk check-in/check-out karyawan.
2. Penerapan kustom (sensor DIY ke Odoo)

Contoh yang umum dibuat di Indonesia:

Kasus	Sensor/Perangkat	Integrasi ke Odoo
Monitoring suhu cold storage	ESP32 + sensor DHT22/DS18B20	Data dikirim via HTTP/MQTT, lalu dicatat ke model custom. Jika suhu melebihi batas, Odoo membuat maintenance request atau notifikasi otomatis.
Maintenance prediktif mesin	Sensor getaran, arus, jam operasi	Jam operasi masuk ke modul Maintenance, dan jadwal perawatan dibuat otomatis berdasarkan data aktual.
Smart farming/greenhouse	Sensor kelembapan tanah, pH, suhu	Data masuk ke Odoo, dan jika kelembapan rendah, task penyiraman dibuat di modul Project atau Field Service.
Tracking stok otomatis	Load cell di rak/bin	Perubahan berat dihitung jadi perubahan stok, dan jika di bawah minimum, reordering rule menghasilkan purchase order.
Penghitung produksi	Sensor proximity/counter di conveyor	Jumlah output produksi masuk otomatis ke Manufacturing Order.
Monitoring energi	Smart meter (PZEM)	Konsumsi listrik per mesin atau line dicatat sebagai biaya produksi.
3. Cara integrasi umum
Sensor (ESP32/Arduino) membaca data.
Data dikirim lewat MQTT atau HTTP POST. Bisa lewat broker seperti Mosquitto dan Node-RED sebagai penghubung.
Odoo menerima data lewat JSON-RPC/XML-RPC API atau controller custom.
Di Odoo, data disimpan, lalu automated action atau server action memicu tindakan (alert, work order, PO, dll.).

Contoh kode sederhana pengiriman data dari Python ke Odoo:

python
import xmlrpc.client

url, db, user, pwd = "https://odoo.example.com", "mydb", "admin", "password"
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, user, pwd, {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

models.execute_kw(db, uid, pwd, "x_sensor.log", "create", [{
    "x_name": "Cold Storage 1",
    "x_temperature": 4.5,
}])
Catatan
Daftar perangkat yang didukung IoT Box dan fitur modul IoT bisa berbeda antarversi Odoo. Cek dokumentasi resmi Odoo untuk versi yang kamu pakai.
Modul IoT resmi tersedia di edisi Enterprise. Di Community, kamu bisa memakai pendekatan kustom (API + MQTT) atau modul dari komunitas (OCA/Odoo Apps).

Kalau kamu ceritakan bidang usahamu (retail, pabrik, pertanian, gudang, dll.), aku bisa bantu merancang arsitektur dan contoh implementasi yang lebih spesifik.
