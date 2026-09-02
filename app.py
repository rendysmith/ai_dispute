"""
ai_dispute API — FastAPI-сервис для сбора и анализа отзывов.

POST /api/v1/data/get_feedbacks — получить отзывы по адресу: ?link=...&topic=... (Basic Auth)
POST /run                      — запустить pipeline: multi_pars → review_analysis (2 прохода)
GET  /tasks/{id}               — статус фоновой задачи
GET  /capacity                 — занятость ресурсов пода и сколько ещё запусков влезет
GET  /healthz                  — healthcheck для k8s

Ресурсы: перед каждым запуском проверяется свободная мощность пода
(см. utils/scheduler.py) — минимум 1 запуск каждой точки гарантирован,
дальнейшие — только если хватает CPU/памяти. При нехватке — HTTP 429.
Время жизни задачи ограничено таймаутом (TASK_TIMEOUT_SEC / FEEDBACK_TIMEOUT_SEC) —
зависнуть не может, при превышении задача отменяется (браузеры закрываются).

Авторизация: точки (кроме /healthz) требуют Basic Auth —
логин/пароль из env HOST_USERNAME / HOST_PASSWORD (те же, что для запроса к ферме).
Если креды не заданы — точки открыты (локальная разработка).
"""
import asyncio
import logging
import os
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from ai.ai_contestation import multi_pars, review_analysis, blocks_ya_reviews_api
from utils.scheduler import make_scheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('contestation-api')

app = FastAPI(title='ai_dispute API', version='1.0.0')

# Хранилище задач (in-memory; для одной реплики k8s этого достаточно)
TASKS: dict[str, dict] = {}
RUNNING_SS: set[str] = set()

MAX_TASKS_KEEP = 200

# Авторизация точек API: Basic Auth — логин/пароль (те же, что для запроса к ферме)
HOST_USERNAME = os.environ.get('HOST_USERNAME', '')
HOST_PASSWORD = os.environ.get('HOST_PASSWORD', '')

# Время жизни задач: /run может идти часами, /get_feedback — это запрос-ответ (минуты)
TASK_TIMEOUT_SEC = float(os.environ.get('TASK_TIMEOUT_SEC', str(8 * 3600)))
FEEDBACK_TIMEOUT_SEC = float(os.environ.get('FEEDBACK_TIMEOUT_SEC', '900'))

scheduler = make_scheduler()

basic_auth = HTTPBasic(auto_error=False)


async def require_auth(credentials: HTTPBasicCredentials | None = Depends(basic_auth)):
    """
    Авторизация точек: Basic Auth по HOST_USERNAME / HOST_PASSWORD.
    Если креды не заданы — авторизация отключена (локальная разработка).
    """
    if not HOST_USERNAME or not HOST_PASSWORD:
        return

    if credentials is not None:
        user_ok = secrets.compare_digest(credentials.username, HOST_USERNAME)
        pass_ok = secrets.compare_digest(credentials.password, HOST_PASSWORD)
        if user_ok and pass_ok:
            return

    raise HTTPException(
        status_code=401,
        detail='Неверные учётные данные',
        headers={'WWW-Authenticate': 'Basic realm="ai-dispute"'},
    )


class RunRequest(BaseModel):
    ss_id: str = Field(..., min_length=1, description='ID Google Sheets таблицы (обязательно)')
    project: str = Field('default', description='Название проекта (вкладка в таблице)')


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _pipeline(ss_id: str, project: str):
    """Сбор отзывов + анализ ИИ (2 прохода — второй добивает пропущенные строки)."""
    await multi_pars(ss_id, project)
    await review_analysis(ss_id, project)
    await review_analysis(ss_id, project)


async def run_pipeline(task_id: str, ss_id: str, project: str):
    """Фоновая задача /run с ограничением времени жизни."""
    task = TASKS[task_id]
    try:
        task.update(status='running', stage='multi_pars', started_at=_now_iso())
        await asyncio.wait_for(_pipeline(ss_id, project), timeout=TASK_TIMEOUT_SEC)

        task.update(status='success', stage='done', finished_at=_now_iso(),
                    result={'message': f'OK: {project}'})
    except asyncio.TimeoutError:
        logger.error('Task %s timeout: превышен лимит %.0fс', task_id, TASK_TIMEOUT_SEC)
        task.update(status='error', stage='error', finished_at=_now_iso(),
                    result={'error': f'Таймаут: задача не завершилась за {TASK_TIMEOUT_SEC:.0f}с'})
    except Exception as ex:
        logger.exception('Pipeline failed: ss_id=%s project=%s', ss_id, project)
        task.update(status='error', stage='error', finished_at=_now_iso(),
                    result={'error': str(ex)})
    finally:
        await scheduler.release('run')
        RUNNING_SS.discard(ss_id)


@app.post('/run', status_code=202)
async def run(req: RunRequest, _auth=Depends(require_auth)):
    if req.ss_id in RUNNING_SS:
        raise HTTPException(status_code=409, detail='Задача для этого ss_id уже выполняется')

    ok, msg = await scheduler.try_acquire('run')
    if not ok:
        raise HTTPException(status_code=429, detail=msg)

    # Убираем старые завершённые задачи, чтобы хранилище не росло бесконечно
    if len(TASKS) > MAX_TASKS_KEEP:
        for tid in [t for t, v in TASKS.items() if v['status'] in ('success', 'error')][:len(TASKS) - MAX_TASKS_KEEP]:
            TASKS.pop(tid, None)

    task_id = str(uuid.uuid4())
    TASKS[task_id] = {
        'id': task_id,
        'ss_id': req.ss_id,
        'project': req.project,
        'status': 'pending',
        'stage': 'queued',
        'created_at': _now_iso(),
    }
    RUNNING_SS.add(req.ss_id)

    asyncio.create_task(run_pipeline(task_id, req.ss_id, req.project))
    logger.info('Task %s started: ss_id=%s project=%s', task_id, req.ss_id, req.project)

    return {'task_id': task_id, 'status': 'pending', 'ss_id': req.ss_id, 'project': req.project}


@app.post('/api/v1/data/get_feedbacks')
async def get_feedbacks(link: str = Query(..., min_length=1,
                                          description='Адрес страницы с отзывами (Яндекс, 2GIS и т.д.)'),
                        topic: str | None = Query(default=None,
                                                  description='Тема/раздел (опционально, для будущих парсеров)'),
                        _auth=Depends(require_auth)):
    """
    Получение отзывов по адресу страницы (без записи в Google-таблицу).

    Контракт совпадает с GetBlock из другого проекта:
    POST /api/v1/data/get_feedbacks?link=...&topic=... + Basic Auth.

    Сейчас поддерживается Яндекс (reviews.yandex.ru и org-страницы Карт),
    в будущем — 2GIS и другие площадки.
    """
    if '2gis' in link:
        # TODO: парсер отзывов 2GIS (public-api.reviews.2gis.com)
        raise HTTPException(status_code=501, detail='Парсер отзывов 2GIS будет добавлен позже')

    ok, msg = await scheduler.try_acquire('get_feedback')
    if not ok:
        raise HTTPException(status_code=429, detail=msg)

    try:
        result = await asyncio.wait_for(
            blocks_ya_reviews_api(None, link, None, None, [], rating_max=5,
                                  ranking='by_time', max_pages=1),
            timeout=FEEDBACK_TIMEOUT_SEC,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504,
                            detail=f'Таймаут получения отзывов ({FEEDBACK_TIMEOUT_SEC:.0f}с)')
    finally:
        await scheduler.release('get_feedback')


@app.get('/tasks/{task_id}')
async def get_task(task_id: str, _auth=Depends(require_auth)):
    task = TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail='Задача не найдена')
    return task


@app.get('/capacity')
async def capacity(_auth=Depends(require_auth)):
    """
    Сколько одновременных запусков влезает в мощности пода:
    лимиты, текущая нагрузка, свободные CPU/память и сколько ещё
    запусков каждой точки можно стартовать.
    """
    return scheduler.snapshot()


@app.get('/healthz')
async def healthz():
    return {'status': 'ok'}
