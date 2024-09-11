#!/bin/bash

# Параметры SSH
USER="root"  # ваш логин
HOST="109.107.170.133"  # IP-адрес или имя хоста
PASSWORD="zJ4zN7dN4ouY"  # ваш пароль

# Подключение к серверу, переход в нужную директорию и выполнение команды
sshpass -p "$PASSWORD" ssh -tt -o StrictHostKeyChecking=no "$USER@$HOST" << EOF
cd ~/ai_one_off
git pull
docker build -t ai_one_off .
EOF
