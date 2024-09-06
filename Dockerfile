FROM python:3.10

# Установка OpenJDK
RUN apt-get update -y && \
    apt-get install -y default-jre default-jdk

RUN apt-get update -y
RUN apt-get install -y python3-pip

# Устанавливаем необходимые браузеры Playwright
RUN playwright install

#RUN apt-get install -y docker-compose
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
