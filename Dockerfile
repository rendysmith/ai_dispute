FROM python:3.12-slim

# Установка системных зависимостей, включая инструменты сборки
RUN apt-get update --fix-missing -y && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    wget \
    unzip \
    gnupg \
    xvfb \
    jq \
    locales \
    # Зависимости для Chrome
    libglib2.0-0 \
    libnss3 \
    libfontconfig1 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    # Зависимости для компиляции C-расширений Python
    build-essential \
    python3-dev \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update -y \
    && apt-get install -y google-chrome-stable \
    && sed -i '/ru_RU.UTF-8/s/^# //g' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

# Установка переменных окружения для локали
ENV LANG=ru_RU.UTF-8
ENV LANGUAGE=ru_RU.UTF-8
ENV LC_ALL=ru_RU.UTF-8

# Установка chromedriver (через JSON эндпоинты Chrome for Testing)
RUN CHROMEDRIVER_URL=$(wget -qO- https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions-with-downloads.json | jq -r '.channels.Stable.downloads.chromedriver[] | select(.platform=="linux64") | .url') && \
    wget -O /tmp/chromedriver.zip "$CHROMEDRIVER_URL" && \
    unzip /tmp/chromedriver.zip -d /tmp/ && \
    mv /tmp/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    rm -rf /tmp/chromedriver.zip /tmp/chromedriver-linux64 && \
    chmod +x /usr/local/bin/chromedriver

WORKDIR /app

# Копирование и установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install playwright && playwright install --with-deps

# Копирование остальных файлов проекта
COPY . .

# Установка правильных прав для Xvfb (опционально, но часто требуется)
RUN chmod 777 /tmp

# Команда по умолчанию — один воркер парсинга (в k8s индекс задаёт JOB_COMPLETION_INDEX)
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & export DISPLAY=:99 && python3 -u scaling_service.py"]