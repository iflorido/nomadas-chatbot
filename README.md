# Nomadas Surf Park — Chatbot

Chatbot para consulta de reservas, servicios y disponibilidad.
Stack: FastAPI + Claude (Anthropic) + MySQL (Bookly Pro) + ChromaDB (RAG)

## Estructura
```
nomadas-chatbot/
├── app/
│   ├── main.py          ← FastAPI endpoints
│   ├── chat.py          ← Motor Claude + tool use
│   └── tools/
│       ├── bookly.py    ← Queries MySQL a Bookly
│       └── rag.py       ← Sistema RAG con ChromaDB
├── knowledge/
│   └── docs/            ← Añade aquí tus PDFs, TXTs, MDs
├── widget/
│   └── chat.js          ← Widget JS para WordPress
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Configuración

1. Copia `.env.example` a `.env` y rellena tus credenciales:
   - DB_HOST, DB_NAME, DB_USER, DB_PASSWORD (wp-config.php)
   - ANTHROPIC_API_KEY (console.anthropic.com)
   - DB_PREFIX=w6H3p_

2. Añade documentos a `knowledge/docs/` (PDF, TXT o MD)

3. Indexa los documentos:
   ```bash
   docker compose run --rm chatbot python -m app.tools.rag index
   ```

## Despliegue en VPS con Plesk

1. Sube el proyecto al VPS:
   ```bash
   scp -r nomadas-chatbot/ usuario@tu-vps:/var/www/chatbot/
   ```

2. Averigua el nombre de la red Docker de tu WordPress en Plesk:
   ```bash
   docker network ls
   docker inspect <contenedor_wordpress> | grep NetworkMode
   ```

3. Actualiza `docker-compose.yml` con el nombre correcto de la red.

4. Levanta el contenedor:
   ```bash
   cd /var/www/chatbot
   docker compose up -d
   ```

5. En Plesk, crea un subdominio (ej: chat.nomadassurfpark.com)
   y configura un proxy reverso al puerto 8000.

6. Actualiza `API_URL` en `widget/chat.js` con tu subdominio.

7. Añade `chat.js` a WordPress (footer.php o plugin de snippets).

## Test rápido
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hola, qué actividades tenéis?"}]}'
```
