# Deploy Ollama en Coolify — Instrucciones para Carlos

**Proyecto:** CRECE v2.0
**Objetivo:** Correr Ollama con modelo Gemma 3 en el VPS via Coolify
**Prioridad:** Evaluar calidad de respuestas IA. No importa si tarda 60s+, es CPU-only.
**VPS actual:** 16GB RAM total, ~8GB disponibles, sin GPU

---

## 1. Crear nuevo servicio en Coolify

- **Tipo:** Docker Image
- **Imagen:** `ollama/ollama:latest`
- **Nombre del servicio:** `crece-ollama`

## 2. Configuracion de red

**IMPORTANTE: NO exponer al publico.**

- Puerto interno: `11434` (default de Ollama)
- Puerto publico: **ninguno** — solo accesible desde la red interna de Docker
- Si Coolify lo pide, marcar como "internal only" o no asignar dominio/proxy

El backend de CRECE (FastAPI) se conectara por red interna Docker usando:
```
http://crece-ollama:11434
```

## 3. Persistent Volume

Ollama guarda los modelos descargados en `/root/.ollama`. Sin volumen persistente,
re-descarga ~16GB en cada deploy.

- **Mount path en container:** `/root/.ollama`
- **Volume name:** `crece-ollama-data`
- **Tipo:** persistent volume (no bind mount)

## 4. Recursos

- **RAM estimada del modelo:** ~8GB para gemma3:12b
- **CPU:** Sin limite especifico, usara lo que haya disponible
- **Nota:** Con 16GB en el VPS y ~8GB libres, el modelo 12b es el que cabe.
  El 27b necesita ~16GB solo para el y no es viable sin escalar.

## 5. Variables de entorno

No requiere variables obligatorias. Opcionales:

```
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_KEEP_ALIVE=10m
```

- `OLLAMA_HOST`: Escuchar en todas las interfaces (necesario para red Docker)
- `OLLAMA_KEEP_ALIVE`: Mantener modelo en RAM 10 min despues del ultimo request

## 6. Descargar el modelo (post-deploy)

Una vez que el container este corriendo, entrar al shell del container y ejecutar:

```bash
# Modelo recomendado para 8GB disponibles:
ollama pull gemma3:12b
```

Si por alguna razon no cabe o el container crashea, bajar a:
```bash
ollama pull gemma3:4b
```

Para verificar que funciona:
```bash
# Dentro del container
ollama list
ollama run gemma3:12b "Hola, responde en una linea"
```

**Nota:** La primera vez tarda en descargar (~7GB). Despues queda en el volumen persistente.

## 7. Verificar conectividad

Desde el container del backend de CRECE (o cualquier otro en la misma red):

```bash
curl http://crece-ollama:11434/api/tags
```

Debe responder con JSON listando los modelos disponibles.

## 8. Red de Docker en Coolify

El servicio `crece-ollama` debe estar en la **misma red Docker** que el backend de CRECE.

- Si Coolify usa una red compartida por proyecto, verificar que ambos servicios
  (backend y ollama) esten en el mismo proyecto
- Si usa redes aisladas, crear una red compartida o usar la red default de Coolify

**El backend se conectara con:**
```
OLLAMA_BASE_URL=http://crece-ollama:11434
```

## 9. Health check (opcional pero recomendado)

```
curl -f http://localhost:11434/api/tags || exit 1
```

- Intervalo: 30s
- Timeout: 10s
- Retries: 3

---

## Resumen para Coolify

| Config | Valor |
|--------|-------|
| Imagen | `ollama/ollama:latest` |
| Puerto interno | 11434 |
| Puerto publico | ninguno |
| Volume | `/root/.ollama` → `crece-ollama-data` |
| Red | misma que crece-backend |
| Dominio | no asignar |
| Modelo | `gemma3:12b` (recomendado para 8GB libres) |
| RAM estimada | ~8GB |

---

## Despues del deploy (lo hacemos nosotros)

Una vez que Carlos confirme que Ollama esta corriendo y el modelo descargado,
actualizaremos en el backend de CRECE:

```env
OLLAMA_BASE_URL=http://crece-ollama:11434
OLLAMA_MODEL=gemma3:12b
AI_PROVIDER=ollama
```

**Contacto:** Marx Chavez — cualquier duda, preguntar antes de asumir.
