# ERD - Modul aqua_ras

```mermaid
erDiagram
    FARM ||--o{ SYSTEM : punya
    FARM ||--o{ TANK : punya
    FARM ||--o{ GATEWAY : punya
    SYSTEM ||--o{ TANK : "loop RAS"
    TANK ||--o{ DEVICE : "dipasang di"
    GATEWAY ||--o{ DEVICE : "menghubungkan"
    DEVICE ||--o{ READING_AGG : menghasilkan
    DEVICE }o--o| MAINTENANCE_EQUIPMENT : "terhubung"
    ALERT_RULE }o--o{ TANK : "berlaku untuk"
    ALERT_RULE ||--o{ ALERT : memicu
    TANK ||--o{ ALERT : mengalami
    ALERT }o--o| MAINTENANCE_REQUEST : membuat
    TANK ||--o{ BATCH : "siklus"
    BATCH ||--o{ FEEDING : mencatat
    BATCH ||--o{ SAMPLING : mencatat
    BATCH ||--o{ MORTALITY : mencatat
    BATCH ||--o{ HARVEST : mencatat
    BATCH ||--|| ANALYTIC_ACCOUNT : "biaya/HPP"
    TANK ||--o{ WATER_TEST : "uji manual"
    FEEDING }o--o| STOCK_MOVE : "konsumsi pakan"
    HARVEST }o--o| STOCK_MOVE : "hasil panen"
    FEEDING }o--o| PRODUCT : pakan
    HARVEST }o--o| PRODUCT : "produk panen"
    RATION_RULE }o--|| BATCH : "dipakai hitung ration"
```

## Alur data singkat
Sensor -> MQTT -> Node-RED (agregat 1 menit, antrian offline) -> `POST /aqua/ingest` -> `aqua.reading.agg`
-> evaluasi `aqua.alert.rule` -> `aqua.alert` (+ chatter, Telegram, maintenance request, eskalasi).
