#!/usr/bin/env bash
# Автодеплой ai-dispute на VDS.
# Вызывается GitHub Actions по SSH после сборки образа (см. .github/workflows/),
# можно запускать и вручную:  ./deploy/deploy.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/ai-dispute}"
# Репозиторий публичный — конфигурацию тянем прямо из GitHub,
# чтобы compose на сервере всегда совпадал с кодом.
COMPOSE_URL="https://raw.githubusercontent.com/rendysmith/ai_dispute/main/docker-compose.yml"

if [ ! -d "${APP_DIR}" ]; then
    echo "Ошибка: папка ${APP_DIR} не найдена. Сначала выполните одноразовую настройку (deploy/README.md)." >&2
    exit 1
fi

cd "${APP_DIR}"

# Предпроверка обязательных файлов (CI их не создаёт)
[ -f .env ] || { echo "Ошибка: ${APP_DIR}/.env не найден на сервере" >&2; exit 1; }
if [ ! -f secrets/service_account.json ]; then
    echo "Ошибка: secrets/service_account.json не найден на сервере (или Docker создал папку вместо файла)." >&2
    echo "Положите файл: scp service_account.json root@<VDS>:${APP_DIR}/secrets/" >&2
    exit 1
fi

# IMAGE: если в .env нет — добавляем актуальный образ из GHCR,
# чтобы compose не подставил заглушку YOUR_ORG/YOUR_REPO
if grep -q '^IMAGE=' .env; then
    echo "IMAGE уже задан в .env: $(grep '^IMAGE=' .env | head -1)"
else
    echo "IMAGE=ghcr.io/rendysmith/ai_dispute:latest" >> .env
    echo ">>> Добавлено в .env: IMAGE=ghcr.io/rendysmith/ai_dispute:latest"
fi

# Синхронизируем docker-compose.yml из репозитория (если GitHub недоступен —
# работаем с тем, что уже лежит на сервере)
echo ">>> Синхронизируем docker-compose.yml из репозитория..."
if command -v curl >/dev/null 2>&1; then
    if curl -fsSL --max-time 30 "${COMPOSE_URL}" -o docker-compose.yml.new 2>/dev/null \
       && grep -q '^services:' docker-compose.yml.new \
       && grep -q 'secrets/service_account.json' docker-compose.yml.new; then
        mv docker-compose.yml.new docker-compose.yml
        echo "    docker-compose.yml обновлён (${COMPOSE_URL})"
    else
        rm -f docker-compose.yml.new
        echo "    Внимание: не удалось скачать compose из GitHub — используем текущий файл" >&2
    fi
else
    echo "    Внимание: curl не найден — используем текущий docker-compose.yml" >&2
fi

# Проверяем, что в compose есть монтирование сервисного аккаунта
grep -q 'secrets/service_account.json' docker-compose.yml \
    || { echo "Ошибка: docker-compose.yml на сервере не монтирует secrets/service_account.json" >&2; exit 1; }

echo ">>> Качаем свежий образ..."
docker compose pull

echo ">>> Перезапускаем контейнер..."
docker compose up -d --remove-orphans

# Чистим старые образы, чтобы диск не забивался
docker image prune -f >/dev/null 2>&1 || true

echo ">>> Проверяем healthz..."
for i in $(seq 1 45); do
    if curl -fsS http://127.0.0.1:8000/healthz >/dev/null 2>&1; then
        echo "OK: сервис здоров (healthz)."
        docker compose ps
        exit 0
    fi
    sleep 2
done

echo "Ошибка: сервис не ответил на healthz за 90 секунд." >&2
docker compose ps >&2 || true
docker compose logs --tail=80 >&2 || true
exit 1
