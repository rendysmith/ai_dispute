# AI Contestation — развертывание в Kubernetes

Сервис собирает отзывы с сайтов (`multi_pars`) и анализирует их ИИ
(`review_analysis`, запускается дважды — второй проход добивает пропущенные строки).

## API

| Метод | Путь          | Описание                                                                 |
|-------|---------------|--------------------------------------------------------------------------|
| POST  | `/run`        | Запуск pipeline. Body: `{"ss_id": "...", "project": "default"}`. `ss_id` обязателен, `project` по умолчанию `default`. Возвращает `202` + `task_id` |
| POST  | `/api/v1/data/get_feedbacks` | Получение свежих отзывов по адресу. Параметры: `link` (обязательно), `topic` (опционально). Возвращает `{"datas": {...}, "items_written": N, "rating_score": ..., "review_count": N}` без записи в таблицу |
| GET   | `/tasks/{id}` | Статус задачи: `pending/running/success/error` + текущий этап            |
| GET   | `/capacity`   | Ресурсы пода: лимиты, текущая нагрузка, сколько ещё запусков влезет     |
| GET   | `/healthz`    | Healthcheck для k8s (readiness/liveness)                                 |

**Авторизация**: все точки, кроме `/healthz`, требуют **Basic Auth** —
логин/пароль `HOST_USERNAME`/`HOST_PASSWORD` (те же, что для запроса к ферме).
Пример: `curl -u логин:пароль ...` (401 при неверных кредах).

## Ресурсы и одновременные запуски

Перед **каждым** запуском точки сервис проверяет свободные мощности пода:

- лимиты читаются из cgroup контейнера (в k8s это limits из deployment.yaml);
- каждая точка имеет **гарантированный минимум 1 одновременный запуск**
  (первый запуск всегда принимается);
- каждый следующий запуск принимается, только если
  `базовое потребление + вес всех запущенных задач + вес новой задачи ≤ лимиты пода`
  (проверяется и CPU, и память);
- при нехватке ресурсов точка отвечает `429` с текстом, чего именно не хватает;
- веса задач настраиваются в ConfigMap (`TASK_CPU_RUN`, `TASK_MEM_RUN`,
  `TASK_CPU_GET_FEEDBACK`, `TASK_MEM_GET_FEEDBACK`, `BASE_CPU`, `BASE_MEM_GB`).

Пример расчёта для лимитов 2 CPU / 4 ГБ и весов по умолчанию
(база 0.3 CPU / 0.5 ГБ, `run` = 1.0 CPU / 1.5 ГБ, `get_feedback` = 0.7 CPU / 1.0 ГБ):
1 `run` + 1 `get_feedback` = 2.0 CPU / 3.0 ГБ — влезает;
второй `run` = 3.0 CPU — уже нет (429).

Точка `/capacity` показывает живой расчёт:
```json
{"cpu_limit": 2.0, "mem_limit_gb": 4.0, "running": {"run": 1, "get_feedback": 0},
 "load_cpu": 1.3, "load_mem_gb": 2.0, "free_cpu": 0.7, "free_mem_gb": 2.0,
 "capacity_more": {"run": {"by_cpu": 0, "by_mem": 1, "min": 0},
                   "get_feedback": {"by_cpu": 1, "by_mem": 2, "min": 1}}}
```

## Время жизни задач

Каждая задача ограничена таймаутом — зависнуть не может:
- `/run` — `TASK_TIMEOUT_SEC` (по умолчанию 8 часов), при превышении задача
  отменяется (`asyncio.wait_for`), браузеры Playwright закрываются в `finally`,
  статус становится `error` с сообщением о таймауте;
- `/get_feedback` — `FEEDBACK_TIMEOUT_SEC` (по умолчанию 15 минут, это запрос-ответ),
  при превышении — `504`.

Дополнительно все блокирующие HTTP-запросы внутри парсеров имеют свои таймауты,
а если event loop всё же заблокируется целиком — под перезапустит liveness-проба k8s.

Примечание про другие проекты на нодах: контейнер не может выйти за свои limits,
поэтому admission control считает именно лимиты пода (это гарантированный потолок).
Свободные ресурсы всей ноды учитывать kube-scheduler через `resources.requests`.

Пример:

```bash
curl -X POST http://<host>/run -H 'Content-Type: application/json' \
  -u 'логин:пароль' \
  -d '{"ss_id": "1ABC...", "project": "Evotor"}'

# → {"task_id": "3fa85f64-...", "status": "pending", ...}

curl -X POST 'http://<host>/api/v1/data/get_feedbacks?link=https://yandex.md/maps/org/avtomir_mazda/86615003593/reviews/&topic=' \
  -u 'логин:пароль'

# → {"datas": {...}, "items_written": 50, "rating_score": 4.7, "review_count": 695}

curl http://<host>/tasks/3fa85f64-... -u 'логин:пароль'
```

## Требования

- **PostgreSQL** — токены ИИ (`tokens`), правила форумов (`forum_rules`), прокси (`proxies`).
  Сервис падает при старте без доступной БД (токен GPT грузится при импорте модуля).
- **Google Sheets** — сервисный аккаунт уже лежит в репозитории: `utils/service_account.json`
  (попадает в образ через `COPY . .`). ID таблицы передаётся в `ss_id`.
- **2captcha** — `CAPTCHA_KEY` нужен для otzovik.com.

## Переменные окружения

| Переменная          | Где           | Описание                                    |
|---------------------|---------------|---------------------------------------------|
| `HEADLESS`          | ConfigMap     | `true` в контейнере                         |
| `PROXY_ON`          | ConfigMap     | `false` в контейнере                        |
| `MAX_SEC`           | ConfigMap     | макс. пауза между запросами                 |
| `POSTGRESQL_*`      | Secret        | подключение к БД                            |
| `HOST_USERNAME/PASSWORD` | Secret   | доступ к хост-ферме (не используется напрямую) |
| `CAPTCHA_KEY`       | Secret        | ключ 2captcha                               |

## Деплой (автоматический)

Схема: **push в `main` → GitHub Actions собирает Docker-образ → пушит в GHCR → применяет манифесты в k8s → подменяет образ по digest → ждёт rollout**.

### Шаг 1. Одноразовая настройка в кластере (вручную, один раз)

```bash
# 1. Namespace (если ещё нет)
kubectl create namespace <ns>

# 2. Реальный Secret с боевыми значениями (заглушки из репозитория НЕ применяются CI!)
KUBE_NAMESPACE=<ns> \
POSTGRESQL_HOST=... POSTGRESQL_PORT=5432 POSTGRESQL_DB=... \
POSTGRESQL_USERNAME=... POSTGRESQL_PASSWORD=... \
HOST_USERNAME=... HOST_PASSWORD=... \
CAPTCHA_KEY=... API_TOKEN=... \
./deploy/setup-secret.sh
```

`deploy/k8s/secret.yaml` в репозитории — только шаблон, CI его не применяет,
чтобы не затереть боевые значения.

### Шаг 2. Секреты GitHub (Settings → Secrets and variables → Actions)

| Секрет | Описание |
|--------|----------|
| `KUBE_CONFIG_B64` | kubeconfig кластера в base64 (`base64 -w0 ~/.kube/config`). У пользователя должны быть права на namespace (deployments/services/configmaps) |
| `KUBE_NAMESPACE` | Namespace для деплоя (необязательно, по умолчанию `default`) |

Логин в GHCR происходит автоматически через `GITHUB_TOKEN`.

> Если репозиторий **приватный** — k8s не сможет скачать образ без pull-секрета:
> создайте PAT с правами `read:packages`, затем
> `kubectl create secret docker-registry ghcr-pull --docker-server=ghcr.io --docker-username=<user> --docker-password=<PAT> -n <ns>`
> и добавьте в `deploy/k8s/deployment.yaml`:
> ```yaml
> spec:
>   imagePullSecrets:
>     - name: ghcr-pull
> ```
> Для публичного репозитория это не нужно.

### Шаг 3. Пуш — и всё

```bash
git push origin main
```

GitHub Actions: `Build → Deploy`. Следить можно на вкладке Actions репозитория.

### Проверка после деплоя

```bash
kubectl -n <ns> get pods -l app=ai-contestation
kubectl -n <ns> logs -l app=ai-contestation --tail=50
kubectl -n <ns> port-forward svc/ai-contestation 8000:80
curl http://localhost:8000/healthz          # {"status":"ok"}
curl http://localhost:8000/capacity         # ресурсы пода
curl -X POST http://localhost:8000/get_feedback -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_TOKEN>' \
  -d '{"url": "https://yandex.md/maps/org/avtomir_mazda/86615003593/reviews/"}'
```

### Если деплой не прошёл

- `kubectl -n <ns> describe pod -l app=ai-contestation` — ошибки запуска (ImagePullBackOff → приватный репозиторий, CreateContainerConfigError → нет Secret);
- `kubectl -n <ns> get events --sort-by=.lastTimestamp | tail` — события кластера;
- вкладка Actions в GitHub — на каком шаге упало (обычно: нет `KUBE_CONFIG_B64` или нет прав у kubeconfig).

## Локальный запуск

```bash
cp .env.example .env   # заполнить реальными значениями
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Важно про парсинг

- В Google-таблице должен быть лист `links` с колонками: `link`, `status`, `max_raiting`, `last_page`.
- Каждый парсер открывает/закрывает свой Playwright-браузер — параллельные запросы не мешают друг другу.
- Если парсер упал — в колонку `status` пишется текст ошибки, строка будет переобработана при следующем запуске.
- `review_analysis` в endpoint запускается дважды: первый проход может пропускать строки
  (лимиты ИИ/сети), второй проход обрабатывает только незаполненные.
