FROM python:3.10

RUN apt-get update -y
RUN apt-get install -y python3-pip

# Устанавливаем Playwright и необходимые браузеры
RUN pip install playwright
RUN playwright install

# Обновите список пакетов и установите необходимые библиотеки
RUN apt-get update && \
    apt-get install -y \
        libx11-xcb1 \
        libxrandr2 \
        libxcomposite1 \
        libxcursor1 \
        libxdamage1 \
        libpci3 \
        libgl1-mesa-glx \
        libxfixes3 \
        libxi6 \
        libgtk-3-0 \
        libatk1.0-0 \
        libasound2 \
        libdbus-1-3 && \
    apt-get clean

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
