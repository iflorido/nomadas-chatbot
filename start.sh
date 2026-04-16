#!/bin/bash
set -e

# Verificar que las variables críticas están presentes
if [ -z "$OPENAI_API_KEY" ] && [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ ERROR: No se encontró OPENAI_API_KEY ni ANTHROPIC_API_KEY en el entorno."
    echo "   Asegúrate de que el .env está correctamente montado con env_file en docker-compose.yml"
    exit 1
fi

echo "✅ Variables de entorno cargadas (LLM_PROVIDER=$LLM_PROVIDER)"
echo "🔍 Indexando documentos de knowledge/docs/..."
python -m app.tools.rag index

echo "🚀 Arrancando servidor en puerto 8018..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8018