# SIMS – Microservicio IoT FastAPI
**Versión:** Sprint 5 – First Deployment  
**Fecha:** 2026-02-23

---

## Descripción General

Este repositorio contiene el microservicio IoT de SIMS, desarrollado en FastAPI y scripts Python. Permite la recolección y envío de datos de sensores/vehículos al backend, garantizando autenticación y validación mínima.

---

## Arquitectura y Componentes

- **FastAPI:** Endpoints para recepción de datos IoT autenticados.
- **Scripts Agente:** Envían datos al backend usando API key.
- **Validación:** Estructura y tipos de datos comprobados antes de almacenar o reenviar.
- **Autenticación:** API key obligatoria en headers para todas las peticiones IoT.

---

## Integración

- **Backend Laravel:** Recibe y almacena datos enviados por los agentes IoT.
- **API Key:** Variable de entorno `API_KEY` obligatoria en scripts y backend.

---

## Endpoints y Scripts Principales

| Script/Endpoint      | Descripción                        | Seguridad         |
|---------------------|------------------------------------|-------------------|
| /api/command (POST) | Recibe comandos IoT                | API key           |
| agent.py            | Envía datos periódicos al backend  | API key           |
| Otros scripts       | Simulación/control de sensores      | API key           |

---

## Seguridad y Validaciones

- **API key en todas las peticiones.**
- **Validación básica de estructura y tipos.**
- **Variables de entorno para configuración.**

---

## Despliegue y Entorno

- Variables de entorno en `.env` (no exponer credenciales reales).
- Docker y `docker-compose.yml` disponibles.
- Requiere Python 3.9+, FastAPI, requests.

---

## Estado Actual

- Scripts y endpoints completos y auditados.
- Seguridad mínima y validación garantizadas.
- Listo para integración y despliegue.

---

## Recomendaciones

- Reforzar validaciones y logs en futuros sprints.
- Documentar ejemplos de payloads y respuestas.

---

**Fin del README – IoT SIMS**
