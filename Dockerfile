FROM python:3.12-bookworm

# Обновление списка пакетов и установка pip
RUN apt-get update -y && \
    apt-get install -y python3-pip

RUN pip install --upgrade pip

RUN pip install playwright==1.47.0 && \
    playwright install --with-deps

RUN mkdir /app/

COPY ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY . /app/
WORKDIR /app/

ENV PRJPATH /app/

# Добавление команды для предоставления прав на выполнение файла
RUN chmod +x run_container.sh
RUN chmod +x restart_build.sh

# Запуск основного файла
CMD ["python", "-um", "main"]
