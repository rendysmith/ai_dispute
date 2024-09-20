FROM python:3.10

# Обновление списка пакетов и установка pip
RUN apt-get update -y && \
    apt-get install -y python3-pip firefox-esr

RUN pip install --upgrade pip

# Установка Playwright
RUN pip install playwright==1.47.0

# Установка браузеров и зависимостей для Playwright (с правами root)
RUN  useradd -m -p securepassword root && \
     usermod -aG sudo root && \
     echo "root:securepassword" | chpasswd && \
     sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
     sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd && \
     echo "export VISUDO_ASKCC=0" >> /etc/profile && \
     echo "Defaults    env_keep += \"VISUDO_ASKCC\"" >> /etc/sudoers
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