# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**klio-01** is a vehicle inspection prototype that detects and verifies license plate numbers and VINs from images (jpg/jpeg/png). Insurance damage adjusters submit vehicle photos; the system uses pre-trained YOLO models to extract registration and VIN data, then validates those values against SQLite databases.

This is a **greenfield project** — the architecture is fully specified in [doc/task.md](doc/task.md) but implementation is not yet started. Model the project structure on `git@github.com:pmscottx/cc-app-005.git`.

## Tech Stack

- **Language**: Python, managed with **Poetry**
- **API Framework**: FastAPI (each service exposes a REST API)
- **Message Broker**: RabbitMQ (event-driven communication between services)
- **Databases**: SQLite (`licenceplate.db`, `vin.db`)
- **ML Inference**: YOLO (pre-trained `.pt` weights, not trained in this repo)
- **Containerization**: Docker + Docker Compose
- **Frontend**: Bootstrap web UI

## Commands

Each microservice is a separate Poetry project. From a service directory:

```bash
poetry install          # install dependencies
poetry run uvicorn main:app --reload --port <PORT>  # run service locally
poetry run pytest       # run tests
poetry run pytest tests/test_foo.py::test_bar  # run a single test
```

From the repo root (once docker-compose.yml exists):

```bash
docker compose up --build   # start all services
docker compose down         # stop all services
```

## Architecture

The system follows a microservices pattern with these patterns: API Gateway, Service Discovery, Config Server, Circuit Breaker, Event-Driven.

### Services and Ports

| Service | Port | Role |
|---|---|---|
| Config Server | 8000 | Centralized configuration |
| Service Registry | 8001 | Service discovery |
| API Gateway | 8080 | Routing, auth, rate limiting, circuit breaker |
| BusinessLogic | 8010 | Orchestrates the overall workflow |
| Cids | 8011 | Data service |
| Orchestrator | 8012 | Process coordination |
| LicencePlateDetector | 8013 | YOLO inference using `licenceplate-model.pt` |
| VinDetector | 8014 | YOLO inference using `vin-model.pt` |
| LicencePlateValidator | 8015 | Validates detected plates against `licenceplate.db` |
| VinValidator | 8016 | Validates detected VINs against `vin.db` |
| Web App | 8090 | Bootstrap frontend (client) |
| RabbitMQ | 5672 | Message broker |

### Event Flow (RabbitMQ)

```
LicencePlateDetector --[licenceplate.detected]--> LicencePlateValidator
VinDetector          --[vin.detected]-----------> VinValidator
LicencePlateValidator --[licenceplate.checked]--> BusinessLogic
VinValidator          --[vin.checked]-----------> BusinessLogic
```

### Data Models

**licenceplate.db** — table `LICENCEPLATE`:
- `licenceplate` (String, PK)
- `desc` (String)

**vin.db** — table `VIN`:
- `vin` (String, PK)
- `car` (String)
- `production_year` (Date)

## YOLO Model Files

Place pre-trained weights in the `/models/` directory before running detector services:
- `models/licenceplate-model.pt` — used by LicencePlateDetector
- `models/vin-model.pt` — used by VinDetector
