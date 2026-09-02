FROM python:3.12-slim

# Локализация (нужна для корректных дат на русском)
RUN apt-get update --fix-missing -y && \
    apt-get install -y --no-install-recommends locales && \
    sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen && \
    locale-gen && \
    rm -rf /var/lib/apt/lists/*

ENV LANG=ru_RU.UTF-8
ENV LANGUAGE=ru_RU.UTF-8
ENV LC_ALL=ru_RU.UTF-8

WORKDIR /app

# Копирование и установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    # Только headless-shell (в контейнере браузеры всегда headless) —
    # образ заметно меньше и быстрее скачивается на VDS
    playwright install --with-deps --only-shell chromium && \
    # Нормализуем mtime созданных файлов/папок: без этого слой с зависимостями
    # меняется при КАЖДОЙ сборке (pip/apt пишут текущее время), и VDS снова
    # скачивает сотни МБ по медленному каналу. С фиксированными mtime слой
    # переиспользуется между сборками, и деплой тянет только код (килобайты).
    find /usr/local /root /ms-playwright /usr/lib /usr/share \
         -newer /etc/hostname -exec touch -h -d '2020-01-01 UTC' {} + 2>/dev/null || true

# Копирование остальных файлов проекта
COPY . .

EXPOSE 8000

# Запуск FastAPI-сервиса
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
