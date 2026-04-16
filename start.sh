#!/bin/bash
set -e

echo "🔍 Indexando documentos de knowledge/docs/..."
python -m app.tools.rag index

echo "🚀 Arrancando servidor..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8018