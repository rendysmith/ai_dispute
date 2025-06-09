FROM python:3.10-slim

# Установка системных зависимостей
RUN apt-get update --fix-missing -y && \
    apt-get install -y --no-install-recommends \
    python3-pip \
    wget \
    unzip \
    gnupg \
    xvfb \
    # Зависимости для Chrome
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxrender1 \
    libxtst6 \
    libxi6 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update -y \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Установка chromedriver (версия должна соответствовать Chrome)
RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}' | cut -d'.' -f1) && \
    CHROMEDRIVER_VERSION=$(wget -qO- https://chromedriver.storage.googleapis.com/LATEST_RELEASE_$CHROME_VERSION) && \
    wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip && \
    chmod +x /usr/local/bin/chromedriver

WORKDIR /app

# Копирование и установка Python-зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копирование остальных файлов проекта
COPY . .

# Установка правильных прав для Xvfb
RUN chmod 777 /tmp

# Команда запуска с виртуальным дисплеем
CMD ["sh", "-c", "Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset & export DISPLAY=:99 && python3 -um main"]