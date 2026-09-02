#!/usr/bin/env bash
# Автодеплой ai-dispute на VDS.
# Вызывается GitHub Actions по SSH после сборки образа (см. .github/workflows/),
# можно запускать и вручную:  ./deploy/deploy.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-dispute}"

if [ ! -d "${APP_DIR}" ]; then
    echo "Ошибка: папка ${APP_DIR} не найдена. Сначала выполните одноразовую настройку (deploy/README.md)." >&2
    exit 1
fi

cd "${APP_DIR}"

echo ">>> Качаем свежий образ..."
docker compose pull

echo ">>> Перезапускаем контейнер..."
docker compose up -d --remove-orphans

# Чистим старые образы, чтобы диск не забивался
docker image prune -f >/dev/null 2>&1 || true

echo ">>> Проверяем healthz..."
for i in $(seq 1 15); do
    if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
        echo "OK: сервис здоров (healthz)."
        docker compose ps
        exit 0
    fi
    sleep 2
done

echo "Ошибка: сервис не ответил на healthz за 30 секунд. Смотрите: docker compose logs ai-dispute" >&2
exit 1
