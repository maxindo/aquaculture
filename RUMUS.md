# Rumus yang dipakai

| KPI | Rumus | Catatan |
|---|---|---|
| Biomassa (kg) | `populasi_sekarang x ABW_g / 1000` | ABW dari sampling terakhir |
| Populasi sekarang | `tebar - mortalitas - panen(ekor)` | |
| SR (%) | `(populasi_sekarang + panen_ekor) / tebar x 100` | |
| Pertambahan biomassa | `biomassa_sekarang + panen_kg - biomassa_awal` | bobot ikan mati diabaikan |
| FCR | `total_pakan_kg / pertambahan_biomassa` | makin kecil makin efisien |
| ADG (g/hari) | `(ABW_akhir - ABW_awal) / umur_hari` | |
| SGR (%/hari) | `(ln ABW_akhir - ln ABW_awal) / umur_hari x 100` | |
| Ration (kg/hari) | `biomassa x %ration(ABW) x faktor_suhu / 100` | tabel `aqua.ration.rule` |
| Faktor suhu | <20: 0,3 / 20-24: 0,6 / 24-26: 0,85 / 26-31: 1,0 / 31-33: 0,8 / >33: 0,5 | contoh nila, ubah di `ration.py` |
| Penundaan pakan | DO rata-rata 1 jam < 4 mg/L -> ration = 0 | |
| HPP/kg | `(benih + pakan + biaya analytic lain) / kg panen` | |

## Amonia tak-terionisasi (NH3)
```
pKa = 0.09018 + 2729.92 / (T°C + 273.15)
NH3 = TAN / (1 + 10^(pKa - pH))
```
Contoh: TAN 1,0 mg/L, 28 °C, pH 8,0 -> NH3 = 0,065 mg/L (toksik untuk banyak spesies; segera tindak).

## Peringatan
Tabel ration dan faktor suhu adalah **contoh umum nila**. Validasi dengan teknisi budidaya / produsen pakan
untuk spesies, ukuran, dan kepadatan Anda sebelum dipakai di produksi.
