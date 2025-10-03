# Шаг 1: Используйте официальный Python образ (рекомендуется для стабильности)
FROM python:3.12-slim

# Шаг 2: Установка системных зависимостей
# Добавлены пакеты для сборки (build-essential, libssl-dev),
# а также зависимости для asyncpg (libpq-dev) и pyscreeze/Pillow (libjpeg-dev, zlib1g-dev).
RUN apt-get update --fix-missing -y && \
    apt-get install -y --no-install-recommends \
    # Основные утилиты
    python3-pip \
    wget \
    unzip \
    jq \
    gnupg \
    # Зависимости для Chrome/Selenium/PyVirtualDisplay
    xvfb \
    libglib2.0-0 \
    libnss3 \
    # СИСТЕМНЫЕ ЗАВИСИМОСТИ ДЛЯ PYTHON-ПАКЕТОВ
    build-essential \
    libpq-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    # Очистка кэша apt
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Шаг 3: Установка и настройка Chrome/Chromedriver (оставлено как было)
# Этот блок отвечает за установку браузера и драйвера для Selenium
RUN CHROMEDRIVER_URL=$(wget -qO- https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chrome[] | select(.platform=="linux64") | .url') && \
    CHROME_URL=$(wget -qO- https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url') && \
    wget -qO chrome-linux.zip "$CHROMEDRIVER_URL" && \
    wget -qO chromedriver-linux.zip "$CHROME_URL" && \
    unzip chrome-linux.zip && \
    unzip chromedriver-linux.zip && \
    mv chrome-linux/chrome /usr/bin/google-chrome && \
    mv chromedriver-linux/chromedriver /usr/bin/chromedriver && \
    chmod +x /usr/bin/google-chrome /usr/bin/chromedriver && \
    rm chrome-linux.zip chromedriver-linux.zip chrome-linux chromedriver-linux

# Шаг 4: Установка рабочей директории
WORKDIR /app

# Шаг 5: Копирование файла с зависимостями
COPY requirements.txt .

# Шаг 6: Установка Python-зависимостей
# Сначала обновляем инструменты установки
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Устанавливаем все зависимости из файла
RUN pip install --no-cache-dir -r requirements.txt

# Шаг 7: Копирование остального кода
COPY . .

# Шаг 8: Запуск приложения
# Замените эту строку на вашу реальную команду запуска
CMD ["python", "main.py"]