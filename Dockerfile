FROM python:3.10-slim

# Установка системных зависимостей в одном слое для уменьшения размера образа
RUN apt-get update -y && \
    # Установка базовых зависимостей
    apt-get install -y --no-install-recommends \
        ncurses-term \
        python3-pip \
        wget \
        gnupg2 \
        apt-transport-https \
        ca-certificates \
        xvfb \
        xauth && \
    # Добавление репозитория Chrome
    mkdir -p /etc/apt/keyrings && \
    wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /etc/apt/keyrings/google-chrome.gpg && \
    echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list && \
    # Добавление репозитория Mozilla
    wget -q -O - https://packages.mozilla.org/apt/repo-signing-key.gpg | gpg --dearmor -o /etc/apt/keyrings/mozilla.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/mozilla.gpg] https://packages.mozilla.org/apt firefox-stable main" | tee /etc/apt/sources.list.d/mozilla.list && \
    # Обновление списков пакетов и установка браузеров
    apt-get update && \
    apt-get install -y --no-install-recommends \
        firefox-esr \
        google-chrome-stable && \
    # Очистка кэша и ненужных файлов
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    # Обновление pip
    pip install --no-cache-dir --upgrade pip

# Создание рабочей директории
WORKDIR /app

# Копирование и установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование остальных файлов проекта
COPY . .

# Установка переменной окружения
ENV PRJPATH=/app/

# Установка прав на выполнение скриптов
RUN chmod +x run_container.sh restart_build.sh

# Запуск приложения
CMD ["python", "-um", "main"]