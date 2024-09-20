FROM python:3.10

# Обновление списка пакетов и установка pip
RUN apt-get update -y && \
    apt-get install -y python3-pip firefox-esr

RUN apt-get update && apt-get install -y \
    libgbm1 \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer1-0-dev

RUN pip install --upgrade pip

# Установка Playwright
RUN pip install playwright==1.47.0

# Установка браузеров и зависимостей для Playwright (с правами root)

RUN playwright install && \
    rm -rf /root/.cache/ms-playwright/ && \
    playwright install-deps && \
    playwright install

RUN mkdir /app/

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app/
WORKDIR /app/

ENV PRJPATH /app/

# Добавление прав на выполнение скриптов (если необходимо)
RUN chmod +x run_container.sh
RUN chmod +x restart_build.sh

# Запуск основного файла
CMD ["python", "-um", "main"]