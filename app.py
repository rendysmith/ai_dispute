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
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field

from ai.ai_contestation import multi_pars, review_analysis, blocks_ya_reviews_api, _ensure_hpo
from utils.scheduler import make_scheduler

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
logger = logging.getLogger('contestation-api')

@asynccontextmanager
async def lifespan(_: FastAPI):
    # Чистим зомби-браузеры от предыдущих запусков (рестарт после краша
    # контейнера мог оставить процессы) и запускаем сторожевой цикл
    await _cleanup_browsers(BROWSER_STARTUP_CLEAN_SEC, BROWSER_MAX_COUNT)
    watchdog = asyncio.create_task(_watchdog_loop())
    logger.info('watchdog запущен (интервал %dс, браузер старше %dс или сверх %d шт — зомби)',
                WATCHDOG_INTERVAL_SEC, BROWSER_MAX_AGE_SEC, BROWSER_MAX_COUNT)
    yield
    watchdog.cancel()


app = FastAPI(title='ai_dispute API', version='1.0.0', lifespan=lifespan)

# Хранилище задач (in-memory; для одной реплики k8s этого достаточно)
TASKS: dict[str, dict] = {}
RUNNING_SS: set[str] = set()

MAX_TASKS_KEEP = 200

# Сторожевой цикл: чистит зависшие задачи и браузеры-зомби.
# Зомби = chromium/playwright, живущий дольше разумного возраста, либо
# лишний сверх BROWSER_MAX_COUNT: без уборки они копятся и жгут CPU/RAM.
WATCHDOG_INTERVAL_SEC = int(os.environ.get('WATCHDOG_INTERVAL_SEC', '60'))
# Возраст одного браузера не должен превышать время парсинга одной ссылки.
# Всё, что старше — зомби от упавшего/зависшего процесса.
BROWSER_MAX_AGE_SEC = int(os.environ.get('BROWSER_MAX_AGE_SEC', '7200'))
# При старте службы (рестарт после краша) чистим всё старше этого порога
BROWSER_STARTUP_CLEAN_SEC = int(os.environ.get('BROWSER_STARTUP_CLEAN_SEC', '900'))
# Максимум браузерных процессов в контейнере одновременно
# (MAX_CONCURRENT_TASKS задач × до 2 браузеров внутри задачи + запас)
BROWSER_MAX_COUNT = int(os.environ.get('BROWSER_MAX_COUNT', '6'))

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
        # headless/proxy определяются по IP сервера один раз за процесс
        await _ensure_hpo()

        result = await asyncio.wait_for(
            blocks_ya_reviews_api(None, link, None, None, [], rating_max=5,
                                  ranking='by_time', max_pages=1),
            timeout=FEEDBACK_TIMEOUT_SEC,
        )
        return result
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504,
                            detail=f'Таймаут получения отзывов ({FEEDBACK_TIMEOUT_SEC:.0f}с)')
    except Exception as ex:
        logger.exception('get_feedbacks failed: link=%s', link)
        raise HTTPException(status_code=500,
                            detail=f'Ошибка парсинга: {ex}')
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


# ---------------------------------------------------------------------------
# Сторожевой цикл: зависшие процессы Playwright/Chromium и задачи-зомби
#
# Список процессов читается напрямую из /proc: в образе python-slim нет
# утилиты ps (procps не установлен), прежняя версия watchdog на ps молча
# ничего не находила и зомби никогда не убивались.
# ---------------------------------------------------------------------------

def _read_browser_processes() -> list[tuple[int, float, str]]:
    """[(pid, возраст_сек, cmdline)] всех процессов chromium/playwright."""
    try:
        with open('/proc/uptime') as f:
            uptime = float(f.read().split()[0])
    except OSError:
        return []

    try:
        hz = os.sysconf('SC_CLK_TCK') or 100
    except (ValueError, OSError):
        hz = 100

    out: list[tuple[int, float, str]] = []
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue
        try:
            with open(f'/proc/{entry}/cmdline', 'rb') as f:
                cmdline = f.read().replace(b'\x00', b' ').decode(errors='ignore')
            if 'chromium' not in cmdline and 'playwright' not in cmdline:
                continue
            # /proc/<pid>/stat: starttime — поле 22; после закрывающей ')'
            # первое поле — state (№3), поэтому starttime = индекс 19
            with open(f'/proc/{entry}/stat') as f:
                fields = f.read().rsplit(')', 1)[1].split()
            age = uptime - int(fields[19]) / hz
            out.append((int(entry), age, cmdline.strip()[:160]))
        except (OSError, IndexError, ValueError):
            continue
    return out


def _select_zombie_pids(procs: list[tuple[int, float, str]],
                        max_age_sec: float, max_count: int) -> list[tuple[int, float, str]]:
    """Выбирает жертв: старше max_age_sec + самые старые сверх max_count."""
    stale = [pr for pr in procs if pr[1] > max_age_sec]
    young = [pr for pr in procs if pr[1] <= max_age_sec]
    if max_count <= 0:
        excess = young
    else:
        # Убиваем самые старые сверх лимита, самые молодые остаются жить
        young_sorted = sorted(young, key=lambda pr: -pr[1])
        excess = young_sorted[:max(0, len(young_sorted) - max_count)]
    return stale + excess


async def _cleanup_browsers(max_age_sec: float, max_count: int):
    """
    Убивает браузеры-зомби: SIGKILL тем, кто старше max_age_sec, а если
    процессов всё равно больше max_count — самым старым сверх лимита.

    Физический kill — только в контейнере (RUNNING_IN_CONTAINER): там /proc
    видит только процессы контейнера. На машине разработчика /proc общий,
    и под фильтр могут попасть чужие процессы (например, chrome_crashpad
    десктоп-приложений) — там ограничиваемся логом.
    """
    procs = _read_browser_processes()
    if not procs:
        return

    to_kill = _select_zombie_pids(procs, max_age_sec, max_count)
    if not to_kill:
        return

    if not os.environ.get('RUNNING_IN_CONTAINER'):
        logger.warning(
            'watchdog: вне контейнера зомби только логирую, не убиваю (всего %d): %s',
            len(procs),
            '; '.join(f'pid {pid} age={age:.0f}s {cmd[:60]}' for pid, age, cmd in to_kill[:5]),
        )
        return

    logger.warning(
        'watchdog: убиваю браузеры-зомби (всего chromium/playwright: %d): %s',
        len(procs),
        '; '.join(f'pid {pid} age={age:.0f}s {cmd[:80]}' for pid, age, cmd in to_kill[:10]),
    )
    for pid, _, _ in to_kill:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass  # уже умер
        except PermissionError as ex:
            logger.warning('watchdog: нет прав на kill pid %s: %s', pid, ex)


async def _watchdog_loop():
    """Каждые WATCHDOG_INTERVAL_SEC чистит зависшие задачи и зомби-браузеры."""
    while True:
        try:
            await _sweep_stale_tasks()
            await _cleanup_browsers(BROWSER_MAX_AGE_SEC, BROWSER_MAX_COUNT)
        except Exception as ex:
            logger.exception('watchdog: ошибка цикла: %s', ex)
        await asyncio.sleep(WATCHDOG_INTERVAL_SEC)


async def _sweep_stale_tasks():
    """Помечает error задачи, превысившие TASK_TIMEOUT_SEC (страховка от зависаний)."""
    now = datetime.now(timezone.utc)
    for tid, task in list(TASKS.items()):
        if task.get('status') != 'running':
            continue
        started = task.get('started_at')
        if not started:
            continue
        try:
            started_dt = datetime.fromisoformat(started)
        except ValueError:
            continue
        if (now - started_dt).total_seconds() > TASK_TIMEOUT_SEC:
            logger.error('watchdog: задача %s превысила таймаут %.0fс — помечаю error', tid, TASK_TIMEOUT_SEC)
            task.update(status='error', stage='error', finished_at=_now_iso(),
                        result={'error': f'Таймаут: задача не завершилась за {TASK_TIMEOUT_SEC:.0f}с'})
            RUNNING_SS.discard(task.get('ss_id'))
