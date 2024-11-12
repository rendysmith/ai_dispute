FROM python:3.10-slim

# Установка системных зависимостей в одном слое для уменьшения размера образа
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Копирование и установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование остальных файлов проекта
COPY . .

# Установка переменной окружения
ENV PRJPATH=/app/

# Запуск приложения
CMD ["python", "-um", "main"]