#!/bin/bash

# Параметры SSH
USER="root"  # ваш логин
HOST="85.192.49.227"  # IP-адрес или имя хоста
PASSWORD="tqB,u3o9_nHrDV"  # ваш пароль

# Подключение к серверу, переход в нужную директорию и выполнение команды
sshpass -p "$PASSWORD" ssh -tt -o StrictHostKeyChecking=no "$USER@$HOST" << EOF
cd ~/ai_one_off
git pull
docker image prune -f
docker build -t ai_one_off .
EOF
