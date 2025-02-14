FROM python:3.10-slim

# Установка системных зависимостей (минимальный набор)
RUN apt-get update --fix-missing -y && \
    apt-get install -y --no-install-recommends python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Создание рабочей директории
WORKDIR /app

# Обновление pip и установка зависимостей Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование остальных файлов проекта
COPY . .

# Запуск приложения
CMD ["python3", "-um", "main"]
