# klio-01

Prototyp systemu do wykrywania i weryfikacji danych pojazdów ze zdjęć. Przeznaczony dla likwidatorów szkód komunikacyjnych — użytkownik przesyła zdjęcia pojazdu, system wykrywa numer rejestracyjny i VIN przy pomocy algorytmu YOLO, a następnie weryfikuje je w bazach danych i zwraca wynik.

---

## Architektura

System zbudowany w architekturze mikroserwisowej z wzorcami: API Gateway, Service Discovery, Config Server, Circuit Breaker, Event-Driven.

```
┌─────────────────────────────────────────────────────────────────┐
│  KLIENT                                                         │
│  Web App :8090  (Bootstrap UI — upload zdjęć, wyniki)          │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
                    ┌────────▼────────┐
                    │  API Gateway    │  :8080
                    │  Auth / Rate    │
                    │  Circuit Breaker│
                    └────────┬────────┘
                             │ HTTP
                    ┌────────▼────────────────┐
                    │  BusinessLogic Service  │  :8010
                    │  walidacja paczki,      │
                    │  iteracja po zdjęciach  │
                    └──────┬──────────┬───────┘
                           │          │ HTTP
               ┌───────────▼──┐   ┌───▼──────────────────────┐
               │  CIDS :8011  │   │  Orchestrator :8012       │
               │  UUID +      │   │  publikuje zdarzenia      │
               │  stan inspekcji  │  z obrazem (base64)       │
               └──────────────┘   └──┬──────────────────┬─────┘
                                     │ licenceplate.     │ vin.
                                     │ created           │ created
                         ┌───────────▼───────────────────▼──────┐
                         │         RabbitMQ :5672               │
                         │    exchange: microservices (TOPIC)   │
                         └──────┬──────────────────────┬────────┘
                                │ licenceplate.         │ vin.
                                │ created               │ created
                    ┌───────────▼──┐             ┌──────▼────────┐
                    │  LP Detector │             │  VIN Detector │
                    │  :8013  YOLO │             │  :8014   YOLO │
                    └──────┬───────┘             └───────┬───────┘
                           │ licenceplate.               │ vin.
                           │ detected                    │ detected
                         ┌─▼─────────────────────────────▼──────┐
                         │         RabbitMQ :5672               │
                         └──────┬──────────────────────┬────────┘
                                │ licenceplate.         │ vin.
                                │ detected              │ detected
                    ┌───────────▼──────┐   ┌────────────▼─────┐
                    │  LP Validator    │   │  VIN Validator    │
                    │  :8015           │   │  :8016            │
                    │  licenceplate.db │   │  vin.db           │
                    └───────────┬──────┘   └────────────┬──────┘
                                │ licenceplate.          │ vin.
                                │ checked                │ checked
                         ┌──────▼────────────────────────▼──────┐
                         │         RabbitMQ :5672               │
                         └──────────────────┬───────────────────┘
                                            │
                                   ┌────────▼────────┐
                                   │ BusinessLogic   │
                                   │ aktualizuje CIDS│
                                   └─────────────────┘
```

### Przepływ zdarzeń (RabbitMQ)

| Routing key | Producent | Konsument |
|---|---|---|
| `licenceplate.created` | Orchestrator | LicencePlateDetector |
| `vin.created` | Orchestrator | VinDetector |
| `licenceplate.detected` | LicencePlateDetector | LicencePlateValidator |
| `vin.detected` | VinDetector | VinValidator |
| `licenceplate.checked` | LicencePlateValidator | BusinessLogic |
| `vin.checked` | VinValidator | BusinessLogic |

Exchange: `microservices`, typ: TOPIC, trwałe kolejki.

Obrazy przesyłane są w wiadomościach jako base64 (`image_b64`). Orchestrator zwraca natychmiast odpowiedź HTTP — detekcja odbywa się w pełni asynchronicznie.

---

## Serwisy i porty

| Serwis | Port | Opis |
|---|---|---|
| Config Server | 8000 | Centralizowana konfiguracja (JSON per serwis) |
| Service Registry | 8001 | Service discovery + health check co 30 s |
| BusinessLogic | 8010 | Główny serwis — walidacja, iteracja, agregacja wyników |
| CIDS | 8011 | Generuje UUID inspekcji, przechowuje stan |
| Orchestrator | 8012 | Publikuje zdarzenia `licenceplate.created` i `vin.created` do brokera |
| LicencePlateDetector | 8013 | Konsumuje `licenceplate.created`, uruchamia YOLO, publikuje `licenceplate.detected` |
| VinDetector | 8014 | Konsumuje `vin.created`, uruchamia YOLO, publikuje `vin.detected` |
| LicencePlateValidator | 8015 | Weryfikacja tablicy w `licenceplate.db` |
| VinValidator | 8016 | Weryfikacja VIN w `vin.db` |
| API Gateway | 8080 | Routing, auth (X-API-Key), rate limit, circuit breaker |
| Web App | 8090 | Bootstrap UI — upload zdjęć, strona wyników |
| RabbitMQ | 5672 / 15672 | Message broker / panel zarządzania |

---

## Stos technologiczny

| Warstwa | Technologia |
|---|---|
| Język | Python 3.12 |
| Framework API | FastAPI + Uvicorn |
| Zarządzanie zależnościami | Poetry |
| Komunikacja async | RabbitMQ (aio-pika) |
| Bazy danych | SQLite (aiosqlite + SQLAlchemy async) |
| Detekcja ML | YOLO (ultralytics) |
| Konteneryzacja | Docker + Docker Compose |
| Frontend | Bootstrap 5 (Jinja2) |
| Rate limiting | slowapi |
| Circuit breaker | implementacja własna (AsyncCircuitBreaker) |

---

## Wymagania

- Docker 24+ i Docker Compose v2
- (Opcjonalnie) Python 3.12 + Poetry — do lokalnego uruchamiania serwisów

---

## Uruchomienie

### Docker Compose (zalecane)

```bash
# Sklonuj repozytorium
git clone <repo-url>
cd klio-01

# (Opcjonalnie) Umieść wytrenowane modele YOLO
cp /ścieżka/do/licenceplate-model.pt models/
cp /ścieżka/do/vin-model.pt models/

# Zbuduj i uruchom wszystkie serwisy
docker compose up --build

# W tle
docker compose up --build -d

# Zatrzymaj
docker compose down
```

Bez plików `.pt` detektory uruchamiają się w **trybie mock** — zwracają losowe wyniki z predefiniowanej listy. System działa poprawnie end-to-end.

### Lokalnie (pojedynczy serwis)

```bash
cd <nazwa-serwisu>
poetry install
poetry run uvicorn app.main:app --reload --port <PORT>
```

---

## Modele YOLO

Umieść wytrenowane wagi w katalogu `models/` przed uruchomieniem:

```
models/
├── licenceplate-model.pt   # używany przez LicencePlateDetector
└── vin-model.pt            # używany przez VinDetector
```

Katalog jest montowany jako wolumin read-only do kontenerów detektorów. Bez plików `.pt` serwisy przechodzą automatycznie w tryb mock.

---

## Model danych

### licenceplate.db — tabela `LICENCEPLATE`

| Kolumna | Typ | Opis |
|---|---|---|
| `licenceplate` | String (PK) | Numer rejestracyjny |
| `desc` | String | Opis pojazdu |

### vin.db — tabela `VIN`

| Kolumna | Typ | Opis |
|---|---|---|
| `vin` | String (PK) | Numer VIN |
| `car` | String | Model pojazdu |
| `production_year` | Date | Rok produkcji |

### cids.db — tabela `inspections`

| Kolumna | Typ | Opis |
|---|---|---|
| `id` | String (UUID, PK) | Identyfikator inspekcji |
| `status` | String | `pending` / `completed` |
| `image_count` | Integer | Liczba przesłanych zdjęć |
| `licenceplate` | String? | Wykryty numer rejestracyjny |
| `licenceplate_status` | String? | `found` / `not_found` |
| `licenceplate_desc` | String? | Opis z bazy |
| `vin` | String? | Wykryty VIN |
| `vin_status` | String? | `found` / `not_found` |
| `vin_car` | String? | Model pojazdu z bazy |
| `vin_production_year` | Date? | Rok produkcji z bazy |
| `created_at` | DateTime | Data utworzenia |

---

## Dane testowe (seed)

Bazy danych wypełniane są automatycznie przy starcie serwisów.

**licenceplate.db:**

| Numer | Pojazd |
|---|---|
| WW12345 | Toyota Corolla |
| KR54321 | BMW 3 Series |
| GD99001 | Volkswagen Golf |
| PO11223 | Ford Focus |
| WA77654 | Audi A4 |

**vin.db:**

| VIN | Pojazd | Rok prod. |
|---|---|---|
| 1HGBH41JXMN109186 | Honda Civic | 2020 |
| 2T1BURHE0JC028581 | Toyota Corolla | 2018 |
| 3VWFE21C04M000001 | Volkswagen Golf | 2019 |
| WBANA73534B123456 | BMW 3 Series | 2021 |
| WAUZZZ8K9BA012345 | Audi A4 | 2017 |

---

## Konfiguracja

Każdy serwis pobiera konfigurację z Config Server przy starcie (`GET /config/{service_name}`). Pliki JSON znajdują się w [config-server/app/configs/](config-server/app/configs/).

Zmienne środowiskowe (nadpisują wartości domyślne):

| Zmienna | Domyślna wartość | Opis |
|---|---|---|
| `CONFIG_SERVER_URL` | `http://config-server:8000` | URL Config Server |
| `SERVICE_REGISTRY_URL` | `http://service-registry:8001` | URL Service Registry |
| `SERVICE_NAME` | *(nazwa serwisu)* | Nazwa do rejestracji |
| `SERVICE_URL` | *(adres serwisu)* | URL do rejestracji |
| `API_KEY` (web-app) | `demo-key-123` | Klucz API do Gateway |

Klucz API gateway: `demo-key-123` (konfigurowany w [config-server/app/configs/api-gateway.json](config-server/app/configs/api-gateway.json)).

### Symulacja opóźnień detekcji

Detektory obsługują sztuczne opóźnienie konfigurowane w Config Server:

| Serwis | Plik konfiguracyjny | Domyślne opóźnienie |
|---|---|---|
| LicencePlateDetector | `licenceplate-detector.json` | 3 s |
| VinDetector | `vin-detector.json` | 5 s |

Pole `detection_delay` (sekundy). Wartość `0` wyłącza opóźnienie.

---

## API — główne endpointy

Wszystkie żądania zewnętrzne przechodzą przez API Gateway (`http://localhost:8080`). Wymagany nagłówek: `X-API-Key: demo-key-123`.

### Utwórz inspekcję

```
POST /api/inspections
Content-Type: multipart/form-data
X-API-Key: demo-key-123

files: <plik1.jpg>, <plik2.jpg>, ...
```

Odpowiedź `201`:
```json
{ "inspection_id": "550e8400-e29b-41d4-a716-446655440000" }
```

### Pobierz wynik inspekcji

```
GET /api/inspections/{inspection_id}
X-API-Key: demo-key-123
```

Odpowiedź `200`:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "image_count": 2,
  "licenceplate": "WW12345",
  "licenceplate_status": "found",
  "licenceplate_desc": "Toyota Corolla",
  "vin": "1HGBH41JXMN109186",
  "vin_status": "found",
  "vin_car": "Honda Civic",
  "vin_production_year": "2020-03-15",
  "created_at": "2025-01-15T10:30:00"
}
```

Pole `status` przyjmuje wartość `pending` dopóki wyniki z kolejki nie zostaną odebrane. Interfejs webowy odpytuje automatycznie co 3 sekundy.

### Service Registry

```
GET http://localhost:8001/services          # lista wszystkich serwisów
GET http://localhost:8080/api/gateway/breakers  # stan circuit breakerów
```

---

## Weryfikacja działania

Po `docker compose up --build`:

1. **Web UI** — otwórz `http://localhost:8090`, prześlij zdjęcie
2. **Service Registry** — `http://localhost:8001/services` — powinno być 10 serwisów ze statusem `up`
3. **RabbitMQ Management** — `http://localhost:15672` (login: `guest` / `guest`) — po przesłaniu zdjęcia widoczny ruch w kolejkach `licenceplate-detector-q` i `vin-detector-q`
4. **API bezpośrednio** — wyślij plik przez curl:

```bash
curl -X POST http://localhost:8080/api/inspections \
  -H "X-API-Key: demo-key-123" \
  -F "files=@zdjecie.jpg" | jq .
```

---

## Struktura projektu

```
klio-01/
├── docker-compose.yml
├── models/                         # Miejsce na pliki .pt (wagi YOLO)
│   ├── licenceplate-model.pt
│   └── vin-model.pt
├── config-server/                  # Port 8000
├── service-registry/               # Port 8001
├── businesslogic-service/          # Port 8010
├── cids-service/                   # Port 8011
├── orchestrator-service/           # Port 8012
├── licenceplate-detector/          # Port 8013
├── vin-detector/                   # Port 8014
├── licenceplate-validator/         # Port 8015
├── vin-validator/                  # Port 8016
├── api-gateway/                    # Port 8080
└── web-app/                        # Port 8090
```

Każdy serwis ma identyczną strukturę wewnętrzną:

```
<serwis>/
├── Dockerfile
├── pyproject.toml
└── app/
    ├── main.py       # FastAPI app + lifespan (startup/shutdown)
    ├── config.py     # Settings (pydantic-settings) + load_remote_config
    ├── events.py     # RabbitMQ (serwisy event-driven)
    ├── routes.py     # Endpointy FastAPI (serwisy z HTTP API)
    ├── database.py   # SQLAlchemy async (serwisy z DB)
    ├── models.py     # Modele ORM (serwisy z DB)
    ├── schemas.py    # Modele Pydantic (serwisy z DB)
    ├── crud.py       # Operacje na bazie (serwisy z DB)
    └── seed.py       # Dane startowe (serwisy z DB)
```

LicencePlateDetector i VinDetector nie posiadają `routes.py` — są wyłącznie konsumentami zdarzeń RabbitMQ (brak HTTP endpointów dla detekcji).
