#!/usr/bin/env bash
# Одноразовая настройка Secret для ai-dispute в кластере.
# Запускать один раз после создания namespace (НЕ входит в CI-деплой).
#
# Пример:
#   KUBE_NAMESPACE=default \
#   POSTGRESQL_HOST=10.0.0.5 POSTGRESQL_PORT=5432 POSTGRESQL_DB=postgres \
#   POSTGRESQL_USERNAME=postgres POSTGRESQL_PASSWORD=secret \
#   HOST_USERNAME=user@example.com HOST_PASSWORD=secret \
#   CAPTCHA_KEY=2captcha-key API_TOKEN=my-api-token \
#   ./deploy/setup-secret.sh

set -euo pipefail

NS="${KUBE_NAMESPACE:=ai-dispute}"

: "${POSTGRESQL_HOST:=82.97.248.69}"
: "${POSTGRESQL_PORT:=5432}"
: "${POSTGRESQL_DB:=default_db}"
: "${POSTGRESQL_USERNAME:=gen_user}"
: "${POSTGRESQL_PASSWORD:=cCGC>?us<+WO#4}"
: "${HOST_USERNAME:=anku@sidorinlab.ru}"
: "${HOST_PASSWORD:=pass}"
: "${CAPTCHA_KEY:=8b842b59c57de53a5bd42ac7721a8c47}"

kubectl create secret generic ai-dispute-secret \
  -n "${NS}" \
  --from-literal=POSTGRESQL_HOST="${POSTGRESQL_HOST}" \
  --from-literal=POSTGRESQL_PORT="${POSTGRESQL_PORT}" \
  --from-literal=POSTGRESQL_DB="${POSTGRESQL_DB}" \
  --from-literal=POSTGRESQL_USERNAME="${POSTGRESQL_USERNAME}" \
  --from-literal=POSTGRESQL_PASSWORD="${POSTGRESQL_PASSWORD}" \
  --from-literal=HOST_USERNAME="${HOST_USERNAME}" \
  --from-literal=HOST_PASSWORD="${HOST_PASSWORD}" \
  --from-literal=CAPTCHA_KEY="${CAPTCHA_KEY}" \
  --dry-run=client -o yaml | kubectl apply -f -

echo "Secret ai-dispute-secret готов в namespace ${NS}"
