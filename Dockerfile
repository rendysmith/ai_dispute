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
        ca-certificates && \
    # Добавление репозитория Mozilla
    echo "deb http://deb.debian.org/debian/ bullseye main" >> /etc/apt/sources.list && \
    echo "deb http://deb.debian.org/debian/ bullseye-updates main" >> /etc/apt/sources.list && \
    echo "deb http://security.debian.org/debian-security bullseye-security main" >> /etc/apt/sources.list && \
    # Добавление репозитория Chrome
    mkdir -p /etc/apt/sources.list.d && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list && \
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