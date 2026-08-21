# AI Contestation — развертывание в Kubernetes

Сервис собирает отзывы с сайтов (`multi_pars`) и анализирует их ИИ
(`review_analysis`, запускается дважды — второй проход добивает пропущенные строки).

## API

| Метод | Путь          | Описание                                                                 |
|-------|---------------|--------------------------------------------------------------------------|
| POST  | `/run`        | Запуск pipeline. Body: `{"ss_id": "...", "project": "default"}`. `ss_id` обязателен, `project` по умолчанию `default`. Возвращает `202` + `task_id` |
| POST  | `/get_feedback` | Получение свежих отзывов по адресу. Body: `{"url": "..."}`. Возвращает `{"datas": {...}, "items_written": N, "rating_score": ..., "review_count": N}` без записи в таблицу |
| GET   | `/tasks/{id}` | Статус задачи: `pending/running/success/error` + текущий этап            |
| GET   | `/capacity`   | Ресурсы пода: лимиты, текущая нагрузка, сколько ещё запусков влезет     |
| GET   | `/healthz`    | Healthcheck для k8s (readiness/liveness)                                 |

**Авторизация**: если задан env `API_TOKEN`, все точки, кроме `/healthz`,
требуют заголовок `Authorization: Bearer <API_TOKEN>` (401 при неверном токене).

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
  -d '{"ss_id": "1ABC...", "project": "Evotor"}'

# → {"task_id": "3fa85f64-...", "status": "pending", ...}

curl -X POST http://<host>/get_feedback -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <API_TOKEN>' \
  -d '{"url": "https://yandex.md/maps/org/avtomir_mazda/86615003593/reviews/"}'

# → {"datas": {...}, "items_written": 50, "rating_score": 4.7, "review_count": 695}

curl http://<host>/tasks/3fa85f64-...
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

## Деплой

```bash
# 1. Секрет (реальные значения!)
kubectl create secret generic ai-contestation-secret \
  --from-literal=POSTGRESQL_HOST=... \
  --from-literal=POSTGRESQL_PORT=5432 \
  --from-literal=POSTGRESQL_DB=... \
  --from-literal=POSTGRESQL_USERNAME=... \
  --from-literal=POSTGRESQL_PASSWORD=... \
  --from-literal=HOST_USERNAME=... \
  --from-literal=HOST_PASSWORD=... \
  --from-literal=CAPTCHA_KEY=... \
  -n <namespace>

# 2. Манифесты (перед этим замените image в deployment.yaml)
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/deployment.yaml
kubectl apply -f deploy/k8s/service.yaml

# 3. Проверка
kubectl rollout status deployment/ai-contestation
kubectl port-forward svc/ai-contestation 8000:80
curl http://localhost:8000/healthz
```

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
