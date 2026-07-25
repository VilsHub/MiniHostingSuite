#!/bin/bash
sudo docker compose up -d --build
sudo docker compose -f hosting-server-nginx/docker-compose.yml up -d --build