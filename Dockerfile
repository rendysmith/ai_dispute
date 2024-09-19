FROM python:3.10

# Обновление списка пакетов и установка pip
RUN apt-get update -y && \
    apt-get install -y python3-pip

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    libxcb-shm0 \
    libx11-xcb1 \
    libxrandr2 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libgtk-3-0 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libatk1.0-0 \
    libcairo-gobject2 \
    libcairo2 \
    libgdk-pixbuf-2.0-0 \
    libxrender1 \
    libasound2

# Установка Playwright
RUN pip install playwright

# Установка браузеров и зависимостей
RUN playwright install firefox
RUN playwright install-deps

# Установка Playwright и необходимых браузеров
#RUN pip install playwright
#RUN playwright install firefox

## Установка необходимых библиотек для работы Playwright
#RUN apt-get update && \
#    apt-get install -y \
#        libx11-xcb1 \
#        libxrandr2 \
#        libxcomposite1 \
#        libxcursor1 \
#        libxdamage1 \
#        libpci3 \
#        libgl1-mesa-glx \
#        libxfixes3 \
#        libxi6 \
#        libgtk-3-0 \
#        libatk1.0-0 \
#        libasound2 \
#        libdbus-1-3 \
#        libatk-bridge2.0-0 \
#        libcups2 \
#        libnss3 \
#        libnspr4 \
#        libdrm2 \
#        libxkbcommon0 \
#        libatspi2.0-0 \
#        libgbm1 \
#        libpango-1.0-0 \
#        libcairo2 && \
#    apt-get clean



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
