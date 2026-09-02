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
    playwright install --with-deps --only-shell chromium

# Копирование остальных файлов проекта
COPY . .

EXPOSE 8000

# Запуск FastAPI-сервиса
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
