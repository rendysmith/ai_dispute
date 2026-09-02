# Деплой ai-contestation на VDS (автоматический)

Проект разворачивается на **отдельном VDS-сервере** через Docker Compose.
Деплой полностью автоматический: **push в `main` → GitHub Actions собирает Docker-образ,
пушит в GHCR → по SSH заходит на VDS → `docker compose pull && up -d` → проверяет healthz**.

```
GitHub (push в main)
   │
   ▼
GitHub Actions: сборка образа → GHCR (ghcr.io/<owner>/<repo>:latest)
   │
   ▼  (SSH)
VDS: /opt/ai-contestation ── docker compose up -d
     ├── .env                        (секреты/настройки, в git нет)
     ├── secrets/service_account.json (Google service account, в git нет)
     └── docker-compose.yml
```

---

## Шаг 1. Одноразовая настройка VDS (вручную, один раз)

### 1.1 Docker и docker compose

```bash
# Debian/Ubuntu
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER    # перелогиниться после этого
docker compose version           # проверка: v2+
```

### 1.2 Рабочая папка проекта

```bash
sudo mkdir -p /opt/ai-contestation/secrets
sudo chown -R $USER:$USER /opt/ai-contestation
cd /opt/ai-contestation
```

Скопируйте на сервер два файла (из репозитория):
`docker-compose.yml` и `.env.example` → `.env`.

```bash
# .env — реальные значения (шаблон — .env.example в репозитории)
# Обязательно: POSTGRESQL_*, HOST_USERNAME, HOST_PASSWORD (Basic Auth API),
# MAX_SEC, таймауты, веса планировщика (опционально)
# Плюс одна строка с образом:
echo "IMAGE=ghcr.io/<ваш-github>/<репозиторий>:latest" >> .env
chmod 600 .env
```

### 1.3 Google service account

Файл `utils/service_account.json` **намеренно не хранится в git** (это секрет).
Положите его на сервер:

```bash
# локально:  scp utils/service_account.json vds:/opt/ai-contestation/secrets/
scp utils/service_account.json root@<IP>:/opt/ai-contestation/secrets/
```

Контейнер монтирует его в `/app/utils/service_account.json` (см. docker-compose.yml).
Если файла нет — контейнер не стартует с понятной ошибкой.

### 1.4 Доступ к GHCR (только для приватного репозитория)

Если репозиторий **публичный** — этот шаг не нужен, образы скачиваются без логина.

Для приватного — один раз залогиньтесь на сервере (PAT с правом `read:packages`):

```bash
docker login ghcr.io -u <ваш-github-login> -p <PAT>
```

### 1.5 Проверка вручную

```bash
docker compose pull
docker compose up -d
curl http://127.0.0.1:8000/healthz     # {"status":"ok"}
```

---

## Шаг 2. Секреты GitHub (Settings → Secrets and variables → Actions)

| Секрет | Описание |
|--------|----------|
| `VDS_HOST` | IP-адрес или домен VDS |
| `VDS_USER` | SSH-пользователь (root или пользователь с правами на docker) |
| `VDS_SSH_KEY` | Приватный SSH-ключ (`cat ~/.ssh/id_ed25519`), без passphrase |
| `VDS_PORT` | SSH-порт (необязательно, по умолчанию 22) |

SSH-ключ должен быть добавлен в `~/.ssh/authorized_keys` на сервере
(или используется ключ, который уже имеет доступ).

Проверка доступа с вашей машины:
```bash
ssh -i ~/.ssh/id_ed25519 root@<IP> 'docker compose -f /opt/ai-contestation/docker-compose.yml ps'
```

---

## Шаг 3. Пуш — и всё

```bash
git push origin main
```

Что произойдёт (вкладка **Actions** репозитория):
1. `build-and-push-image` — сборка образа, пуш в GHCR (`latest` + `sha-…`);
2. `deploy-to-vds` — SSH на сервер: `docker compose pull` → `up -d` →
   проверка `healthz` (до 30 сек). Если healthz не ответил — job падает и в логах
   показываются последние 50 строк контейнера.

---

## Проверка после деплоя

```bash
# На сервере
docker compose ps                       # статус контейнера
docker compose logs --tail=100 ai-contestation
curl http://127.0.0.1:8000/healthz      # {"status":"ok"}
curl http://127.0.0.1:8000/capacity     # ресурсы

# Снаружи (если порт открыт) или через SSH-туннель:
ssh -L 8000:127.0.0.1:8000 root@<IP>
curl -X POST 'http://127.0.0.1:8000/api/v1/data/get_feedbacks?link=https://yandex.md/maps/org/avtomir_mazda/86615003593/reviews/' \
     -u 'логин:пароль'
```

---

## Обновление вручную / откат

```bash
# Обновление (то же, что делает CI)
cd /opt/ai-contestation && ./deploy/deploy.sh

# Откат на предыдущий образ
docker compose ps --format '{{.Image}}'   # посмотреть текущий
docker compose stop && docker compose rm -f
IMAGE=ghcr.io/<owner>/<repo>:sha-<старый> docker compose up -d
```

---

## Частые проблемы

| Симптом | Причина / решение |
|---------|-------------------|
| Контейнер перезапускается, в логах `RuntimeError: Файл сервисного аккаунта Google не найден` | Нет `secrets/service_account.json` на сервере — положить файл и `docker compose up -d` |
| `CreateContainerConfigError` / `env file .env not found` | Нет `.env` в `/opt/ai-contestation` |
| Контейнер стартует, но `/run` падает с ошибкой БД | PostgreSQL недоступен: проверить `POSTGRESQL_*` в `.env` |
| `ImagePullBackOff` / `pull access denied` | Репозиторий приватный, на сервере не выполнен `docker login ghcr.io` (шаг 1.4) |
| Job `deploy-to-vds` падает: `Permission denied (publickey)` | Неверный `VDS_SSH_KEY` или ключ не в `authorized_keys` |
| Job падает: `Host key verification failed` | Первый SSH с runner'а — в скрипте CI нужно `-o StrictHostKeyChecking=no` (в appleboy/ssh-action добавляется параметром `fingerprint` или `host` в known_hosts). Если ошибка есть — добавьте в workflow `with: fingerprint:` (отпечаток ключа сервера) |

---

## Примечания

- `deploy/k8s/` — манифесты для Kubernetes остались от прежнего плана и больше
  **не используются**; их можно удалить.
- `deploy/setup-secret.sh` — скрипт создания k8s-Secret тоже не нужен для VDS
  (секреты живут в `.env` на сервере). Файл содержит реальные значения — **не пушить**.
- Лимиты ресурсов контейнера: при необходимости задайте в docker-compose.yml
  (`deploy.resources.limits`), планировщик задач внутри сервиса читает их из cgroup.
- Авторизация API: Basic Auth, логин/пароль из `.env` (`HOST_USERNAME`/`HOST_PASSWORD`).
