# Plan: Implementacja systemu klio-01 wg spec step-03

## Context

`feat/step-03` jest czysty (tylko README + .gitignore + doc/task.md). Budujemy kompletną implementację 9 serwisów zgodnie ze zaktualizowanym task.md. Kluczowe różnice względem step-01:

| Aspekt | step-01 (11 serwisów) | step-03 (9 serwisów) |
|---|---|---|
| Serwis wejściowy | BusinessLogic :8010 | Orchestrator :8012 |
| UUID/Stan | CIDS :8011 | UUID Service :8011 + orchestrator.db |
| Walidatory | LP Validator :8015 + VIN Validator :8016 | DBValidator :8015 |
| Transport obrazów | base64 w RabbitMQ | nazwa pliku (obraz na dysku) |
| Zdarzenia | licenceplate/vin.created/detected/checked | picture.created / picture.detected / picture.checked |
| Interfejs web | upload plików | lista nazw plików (dostępnych na FS) |
| Opóźnienie LP | 3 s | **8 s** |
| Opóźnienie VIN | 5 s | **3 s** |

---

## Przepływ zdarzeń

```
WEB  →  POST /api/inspections {"filenames": ["img-1.jpeg", ...]}
      →  API Gateway → Orchestrator
         1. walidacja: min 3 nazwy
         2. POST /uuid/generate → {uuid}
         3. INSERT BOX (uuid, created, picture_number)
         4. FOR EACH filename: publish("picture.created", {inspection_id, filename})
         5. return {"inspection_id": uuid}  ← natychmiast

picture.created → licenceplate-detector-q
  → czyta /app/images/{filename}  → sleep(8)  → YOLO/mock
  → publish("picture.detected", {type:"LICENCEPLATE", value, inspection_id, filename})

picture.created → vin-detector-q
  → czyta /app/images/{filename}  → sleep(3)  → YOLO/mock
  → publish("picture.detected", {type:"VIN", value, inspection_id, filename})

picture.detected → dbvalidator-q
  → type=="LICENCEPLATE": find_licenceplate(value) → wynik
  → type=="VIN":          find_vin(value)          → wynik
  → publish("picture.checked", {type, value, valid, desc/car/year, inspection_id})

picture.checked → orchestrator-q
  → UPDATE BOX (denorm pola + status)
  → INSERT BOX_DETAIL (picture, attr_name, attr_value)

WEB polls GET /api/inspections/{uuid} → Orchestrator → zwraca BOX
```

---

## Struktura katalogów do stworzenia

```
klio-01/
├── docker-compose.yml
├── config-server/
├── service-registry/
├── uuid-service/
├── orchestrator-service/
├── licenceplate-detector/
├── vin-detector/
├── dbvalidator-service/
├── api-gateway/
└── web-app/
```

---

## 1. `config-server/` (port 8000)

Wzorzec: identyczny z step-01 (`app/main.py` — GET /config/{name} + /health).

**Pliki konfiguracyjne `app/configs/`:**
```
api-gateway.json          → {"api_key":"demo-key-123","rate_limit":"60/minute","circuit_breaker_fail_max":3,"circuit_breaker_reset_timeout":30}
uuid-service.json         → {}
orchestrator-service.json → {"rabbitmq_url":"amqp://guest:guest@rabbitmq/","database_url":"sqlite+aiosqlite:////app/data/orchestrator.db","uuid_service_url":"http://uuid-service:8011"}
licenceplate-detector.json→ {"rabbitmq_url":"amqp://guest:guest@rabbitmq/","model_path":"/app/models/licenceplate-model.pt","detection_delay":8,"images_dir":"/app/images"}
vin-detector.json         → {"rabbitmq_url":"amqp://guest:guest@rabbitmq/","model_path":"/app/models/vin-model.pt","detection_delay":3,"images_dir":"/app/images"}
dbvalidator-service.json  → {"rabbitmq_url":"amqp://guest:guest@rabbitmq/","database_url":"sqlite+aiosqlite:////app/data/validator.db"}
```

---

## 2. `service-registry/` (port 8001)

Identyczny z step-01 — `app/main.py` + `app/registry.py` (in-memory dict, GET /services, POST /register, DELETE /deregister/{name}, GET /health, healthcheck co 30s).

---

## 3. `uuid-service/` (port 8011) — NOWY

**Pliki:**
- `pyproject.toml` — deps: fastapi, uvicorn, httpx, pydantic-settings
- `Dockerfile`
- `app/config.py` — wzorzec z step-01 (settings, load_remote_config, register/deregister)
- `app/main.py` — lifespan: load_remote_config, register_service; include router
- `app/routes.py`:
```python
from uuid import uuid4
from fastapi import APIRouter
router = APIRouter(tags=["uuid"])

@router.post("/uuid/generate")
async def generate_uuid():
    return {"uuid": str(uuid4())}
```

---

## 4. `orchestrator-service/` (port 8012) — GŁÓWNA ZMIANA

### Zależności (`pyproject.toml`)
fastapi, uvicorn, httpx, aio-pika, sqlalchemy, aiosqlite, pydantic-settings

### `app/database.py` — wzorzec z step-01 licenceplate-validator/database.py
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
class Base(DeclarativeBase): pass
def make_engine(url): return create_async_engine(url, echo=False)
def make_session_factory(engine): return async_sessionmaker(engine, expire_on_commit=False)
async def create_tables(engine):
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
```

### `app/models.py`
```python
from sqlalchemy import String, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class Box(Base):
    __tablename__ = "BOX"
    uuid: Mapped[str] = mapped_column(String, primary_key=True)
    created: Mapped[str] = mapped_column(String)
    picture_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="pending")
    # denormalizowane pola wynikowe
    licenceplate: Mapped[str | None] = mapped_column(String, nullable=True)
    licenceplate_status: Mapped[str | None] = mapped_column(String, nullable=True)
    licenceplate_desc: Mapped[str | None] = mapped_column(String, nullable=True)
    vin: Mapped[str | None] = mapped_column(String, nullable=True)
    vin_status: Mapped[str | None] = mapped_column(String, nullable=True)
    vin_car: Mapped[str | None] = mapped_column(String, nullable=True)
    vin_production_year: Mapped[str | None] = mapped_column(String, nullable=True)

class BoxDetail(Base):
    __tablename__ = "BOX_DETAIL"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uuid: Mapped[str] = mapped_column(String)
    picture: Mapped[str] = mapped_column(String)
    attr_name: Mapped[str] = mapped_column(String)
    attr_value: Mapped[str] = mapped_column(String)
```

### `app/crud.py`
- `create_box(db, uuid, picture_number)` → INSERT BOX
- `get_box(db, uuid)` → SELECT BOX WHERE uuid=?
- `update_box(db, uuid, **fields)` → UPDATE BOX (licenceplate/vin fields + status)
- `add_box_detail(db, uuid, picture, attr_name, attr_value)` → INSERT BOX_DETAIL

### `app/config.py`
```python
class Settings(BaseSettings):
    config_server_url: str = "http://config-server:8000"
    service_registry_url: str = "http://service-registry:8001"
    service_name: str = "orchestrator-service"
    service_url: str = "http://orchestrator-service:8012"
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq/"
    database_url: str = "sqlite+aiosqlite:////app/data/orchestrator.db"
    uuid_service_url: str = "http://uuid-service:8011"
```
`load_remote_config` odczytuje `rabbitmq_url`, `database_url`, `uuid_service_url`.

### `app/events.py`
- `connect()` / `disconnect()` / `publish(routing_key, payload)` — wzorzec step-01
- `start_consuming(session_factory)`:
  - queue `orchestrator-q`, binding `picture.checked`
  - `on_message`: na podstawie `payload["type"]`:
    - "LICENCEPLATE" → `update_box(licenceplate, licenceplate_status, licenceplate_desc)`
    - "VIN"          → `update_box(vin, vin_status, vin_car, vin_production_year)`
    - po każdej: sprawdź czy box ma obie wartości → jeśli tak, `update_box(status="completed")`
  - `add_box_detail(uuid, filename, attr_name, attr_value)`

### `app/routes.py`
```
POST /inspections
  body: {"filenames": ["img-1.jpeg", ...]}  (JSON)
  - walidacja: len(filenames) < 3 → 422 {"detail": "Należy przesłać min 3 zdjęcia!"}
  - POST {uuid_service_url}/uuid/generate → uuid
  - create_box(db, uuid, len(filenames))
  - for filename in filenames:
      publish("picture.created", {"event":"picture.created", "inspection_id":uuid, "filename":filename})
  - return {"inspection_id": uuid}  HTTP 201

GET /inspections/{uuid}
  - get_box(db, uuid)
  - 404 jeśli brak
  - return Box jako dict (id=uuid, status, image_count=picture_number, licenceplate, ...)
```

### `app/main.py`
```python
# lifespan:
#   load_remote_config()
#   DB init + create_tables()
#   events.connect()
#   events.start_consumer_task(session_factory)
#   register_service()
```

---

## 5. `licenceplate-detector/` (port 8013)

### `app/config.py`
```python
class Settings(BaseSettings):
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq/"
    model_path: str = "/app/models/licenceplate-model.pt"
    detection_delay: int = 8
    images_dir: str = "/app/images"
```

### `app/detector.py`
- `load_model(path)` — próbuje załadować YOLO, jeśli brak pliku → tryb mock
- `detect(image_bytes: bytes) → str | None`:
  - tryb mock: `asyncio.sleep(settings.detection_delay)`, losowy wybór z predefiniowanej listy 5 tablic
  - tryb YOLO: `asyncio.sleep(settings.detection_delay)`, uruchomienie modelu

### `app/events.py`
- `connect()` / `disconnect()` / `publish(routing_key, payload)`
- `start_consuming()`:
  - queue `licenceplate-detector-q`, binding `picture.created`
  - `on_message`:
    ```
    inspection_id = payload["inspection_id"]
    filename = payload["filename"]
    image_bytes = open(f"{settings.images_dir}/{filename}", "rb").read()
    licenceplate = await detector.detect(image_bytes)
    if licenceplate:
        publish("picture.detected", {type:"LICENCEPLATE", value:licenceplate, inspection_id, filename})
    else:
        log no detection
    ```

### `app/main.py`
- lifespan: load_remote_config, load_model, events.connect, start_consumer_task, register_service

---

## 6. `vin-detector/` (port 8014)

Symetrycznie do licenceplate-detector:
- queue `vin-detector-q`, binding `picture.created`
- `detection_delay = 3`
- publish `picture.detected` z `{type:"VIN", value:vin, ...}`
- Mock: losowy VIN z predefiniowanej listy 5 VIN-ów

---

## 7. `dbvalidator-service/` (port 8015) — NOWY (łączy LP + VIN validator)

### Deps: fastapi, uvicorn, httpx, aio-pika, sqlalchemy, aiosqlite, pydantic-settings

### `app/models.py` — dwie klasy ORM
```python
class LicencePlate(Base):
    __tablename__ = "LICENCEPLATE"
    licenceplate: Mapped[str] = mapped_column(String, primary_key=True)
    desc: Mapped[str] = mapped_column(String)

class Vin(Base):
    __tablename__ = "VIN"
    vin: Mapped[str] = mapped_column(String, primary_key=True)
    car: Mapped[str] = mapped_column(String)
    production_year: Mapped[date] = mapped_column(Date)
```

### `app/seed.py` — 5 polskich tablic + 5 VIN-ów
```python
LP_RECORDS = [
    ("WW12345", "Toyota Corolla, Warszawa"),
    ("KR98765", "BMW 3 Series, Kraków"),
    ("PO11223", "Ford Focus, Poznań"),
    ("GD77654", "Volkswagen Golf, Gdańsk"),
    ("WR34567", "Audi A4, Wrocław"),
]
VIN_RECORDS = [
    ("VF1LM1B0H35296680", "Renault Megane", date(2017, 6, 15)),
    ("WAUZZZ8K9BA012345", "Audi A4", date(2019, 3, 20)),
    ("WBA3A5C58CF256551", "BMW 3 Series", date(2012, 11, 8)),
    ("2T1BURHE0JC028581", "Toyota Corolla", date(2018, 9, 1)),
    ("VF7NC5FWC31614893", "Citroën C5", date(2015, 4, 22)),
]
```

### `app/events.py`
- queue `dbvalidator-q`, binding: `picture.detected`
- `on_message`:
  ```
  type = payload["type"]
  value = payload["value"]
  if type == "LICENCEPLATE":
      record = find_licenceplate(db, value)
      publish("picture.checked", {type, value, valid:bool(record),
              desc: record.desc if record else None, inspection_id, filename})
  elif type == "VIN":
      record = find_vin(db, value)
      publish("picture.checked", {type, value, valid:bool(record),
              car: record.car if record else None,
              production_year: record.production_year.isoformat() if record else None,
              inspection_id, filename})
  ```

### `app/main.py`
- lifespan: load_remote_config, DB init + seed, events.connect, start_consumer_task, register_service

---

## 8. `api-gateway/` (port 8080)

Identyczny z step-01 z jedną zmianą w `app/main.py`:
```python
SERVICE_SEGMENT_MAP = {
    "inspections": "orchestrator-service",
}
```

Pozostałe pliki (circuit_breaker.py, proxy.py, registry_client.py, config.py) — kopiuj z step-01.

---

## 9. `web-app/` (port 8090)

### Zmiana interfejsu: submitowanie nazw plików zamiast uploadu

Dostępne pliki (`images/`): `img-1.jpeg`, `img-2.jpeg`, `img-3.jpeg`, `img-4.jpeg`

### `app/main.py`
```python
AVAILABLE_IMAGES = ["img-1.jpeg", "img-2.jpeg", "img-3.jpeg", "img-4.jpeg"]

GET /  → index.html (lista dostępnych plików z checkboxami)

POST /submit
  form field: "filenames" (multiple checkboxes)
  body → POST {API_GATEWAY_URL}/api/inspections  {"filenames": [...]}  X-API-Key
  redirect → /results/{inspection_id}

GET /results/{inspection_id}
  GET {API_GATEWAY_URL}/api/inspections/{inspection_id}  X-API-Key
  render results.html (polling co 3s jeśli status=pending)
```

### `app/templates/index.html`
- Bootstrap 5
- Checkboxes dla 4 dostępnych obrazów (wymagane min 3)
- Submit button "Wyślij do analizy"

### `app/templates/results.html`
- Pokazuje: UUID inspekcji, status, tabela wyników (licenceplate + VIN)
- Polling co 3s jeśli pending

---

## 10. `docker-compose.yml`

```yaml
volumes: orchestrator-db, validator-db, rabbitmq-data

services:
  rabbitmq: (bez zmian)
  config-server: (bez zmian)
  service-registry: (port 8001)
  uuid-service:
    port: 8011
    depends_on: config-server(healthy), service-registry(healthy)
  orchestrator-service:
    port: 8012
    volumes: orchestrator-db:/app/data
    depends_on: config-server, service-registry, rabbitmq, uuid-service(started)
  licenceplate-detector:
    port: 8013
    volumes:
      - ./models:/app/models:ro
      - ./images:/app/images:ro
    depends_on: config-server, service-registry, rabbitmq
  vin-detector:
    port: 8014
    volumes:
      - ./models:/app/models:ro
      - ./images:/app/images:ro
    depends_on: config-server, service-registry, rabbitmq
  dbvalidator-service:
    port: 8015
    volumes: validator-db:/app/data
    depends_on: config-server, service-registry, rabbitmq
  api-gateway:
    port: 8080
    depends_on: config-server(healthy), service-registry(healthy)
  web-app:
    port: 8090
    depends_on: api-gateway
    environment: API_GATEWAY_URL, API_KEY
```

---

## Kolejność implementacji

1. `config-server/` + `service-registry/` — infrastruktura
2. `uuid-service/` — prosta usługa
3. `orchestrator-service/` — DB + routes + events
4. `licenceplate-detector/` + `vin-detector/` — event consumers
5. `dbvalidator-service/` — walidacja
6. `api-gateway/` — proxy
7. `web-app/` — UI
8. `docker-compose.yml`

---

## Weryfikacja

1. `docker compose up --build` — 9 serwisów startuje
2. `http://localhost:8001/services` — 9 serwisów ze statusem `up`
3. `http://localhost:8090` — zaznacz 2 pliki → błąd "Należy przesłać min 3 zdjęcia!"
4. Zaznacz 3+ pliki → strona wyników z UUID, status `pending`
5. Po ~8s (LP) i ~3s (VIN) → status `completed`, wyniki w tabelce
6. RabbitMQ Management (`http://localhost:15672`): kolejki `licenceplate-detector-q`, `vin-detector-q`, `dbvalidator-q`, `orchestrator-q`
7. `http://localhost:8080/api/gateway/breakers` — circuit breakery aktywne
