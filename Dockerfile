FROM python:3.10

# Обновление списка пакетов и установка pip
RUN apt-get update -y && \
    apt-get install -y python3-pip firefox-esr

RUN pip install --upgrade pip

# Установка Playwright
RUN pip install playwright==1.47.0

# Установка браузеров и зависимостей для Playwright
RUN playwright install && playwright install-deps

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
CMD ["python", "-um", "main"]in"]