FROM python:3.10-slim

# Установка системных зависимостей, включая Google Chrome и locales
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    wget \
    gnupg \
    locales \  # Установка пакета locales
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome-keyring.gpg && \
    echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
    locale-gen ru_RU.UTF-8 && \
    update-locale LANG=ru_RU.UTF-8 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Установка переменных окружения
ENV LANG=ru_RU.UTF-8
ENV LC_ALL=ru_RU.UTF-8

# Создание рабочей директории
WORKDIR /app

# Копирование и установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование остальных файлов проекта
COPY . .

# Запуск приложения
CMD ["python3", "-um", "main"]