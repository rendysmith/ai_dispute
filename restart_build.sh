#!/bin/bash
git pull
docker image prune -f
docker build -t ai_one_off .