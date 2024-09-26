#!/bin/bash

# Переменные для авторизации
USERNAME="anku@sidorinlab.ru"
PASSWORD="pass"

# URL для запроса
URL="http://109.107.170.211:8000/api/v1/start_generation"

# Данные для POST запроса
DATA='{
  "prompt": "Кто такой Илон Маск?"
}'

# Выполнение POST запроса с базовой авторизацией через wget
wget --method=POST \
  --header="Content-Type: application/json" \
  --header="Accept: application/json" \
  --user="$USERNAME" \
  --password="$PASSWORD" \
  --body-data="$DATA" \
  "$URL" -O -  # Выводить результат в терминал

