FROM python:3.10-slim

# Установка системных зависимостей в одном слое для уменьшения размера образа
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    ncurses-term\
    python3-pip \
    firefox-esr \
    wget \
    gnupg2 \
    apt-transport-https \
    ca-certificates && \
    # Создание директории для списков источников
    mkdir -p /etc/apt/sources.list.d && \
    # Добавление репозитория и установка Chrome
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends google-chrome-stable && \
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

# Установка Playwright
RUN playwright install --with-deps chromium

# Копирование остальных файлов проекта
COPY . .

# Установка переменной окружения
ENV PRJPATH=/app/

# Установка прав на выполнение скриптов
RUN chmod +x run_container.sh restart_build.sh

# Запуск приложения
CMD ["python", "-um", "main"]