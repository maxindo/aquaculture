Aku buatkan paket lengkapnya: modul Odoo 19 aqua_ras, konfigurasi edge (Mosquitto, Node-RED), firmware ESP32, ERD, dan dokumen rumus.

Paket lengkap sudah aku buat dalam aqua_ras_project.zip. Kodenya lolos cek sintaks Python dan XML, tetapi belum pernah dijalankan di Odoo 19.

Isi paket

aqua_ras/ (modul Odoo 19)

Model: 15 model yang mencakup farm, tangki, perangkat, pembacaan sensor, aturan dan kejadian alarm, batch, pakan, sampling, mortalitas, uji air, dan panen.
Endpoint gateway: /aqua/ingest menerima data agregat dari gateway dengan API key per gateway, tanpa duplikat. /aqua/config mengirim aturan alert ke edge untuk kontrol lokal.
Mesin alert:
Aturan memakai durasi minimum dan histeresis agar tidak ada alarm palsu.
Alarm bisa memicu notifikasi chatter dan Telegram, eskalasi otomatis, serta maintenance request.
Ada watchdog yang membuat alarm bila sensor berhenti mengirim data.
Data buffer lama tidak memicu alarm baru.
Batch dan KPI: FCR, SR, ADG, SGR, biomassa, rekomendasi ration harian (dikoreksi suhu, ditunda bila DO rendah), serta biaya dan HPP per kg lewat analytic account.
Integrasi stok: pakan dan panen otomatis membuat stock move.
Uji air manual: NH₃ dihitung otomatis dari TAN, pH, dan suhu.
Tampilan: kanban tangki berwarna (hijau/oranye/merah), grafik dan pivot sensor, form batch, menu, tiga grup akses, dan unit test.

edge/

docker-compose.yml, Mosquitto beserta ACL, dan flow Node-RED (agregasi 1 menit, antrian offline, kirim ulang otomatis).
Firmware ESP32 dengan fail-safe lokal: aerator cadangan menyala bila DO < 3,5 mg/L walau WiFi atau Odoo mati.

docs/

README.md berisi langkah instalasi, setup, dan uji curl tanpa hardware.
ERD.md dan RUMUS.md.
Perlu kamu perhatikan
Tabel ration dan faktor suhu hanya contoh umum nila. Validasi dengan teknisi budidaya atau produsen pakan sebelum dipakai, begitu juga ambang alert.
Beberapa bagian mungkin perlu penyesuaian di build Odoo 19 kamu. Contohnya struktur grup keamanan, field stock.move, dan atribut kanban. Daftar lengkapnya ada di README bagian 6. Jalankan odoo -d DB -i aqua_ras --test-enable --stop-after-init, lalu kirim log error kalau ada, nanti aku perbaiki.
Belum ada dashboard OWL interaktif. Kanban dan grafik bawaan sudah cukup untuk fase 1-2. OWL, perintah aktuator dari Odoo, dan integrasi auto-feeder ada di daftar pengembangan lanjutan.
