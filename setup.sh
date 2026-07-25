#!/bin/bash

# Make the directories:
mkdir -p /etc/php74/fpm
mkdir -p /etc/php80/fpm
mkdir -p /etc/php81/fpm
mkdir -p /etc/php82/fpm
mkdir -p /etc/php82/ini/
mkdir -p /etc/php81/ini/
mkdir -p /etc/php80/ini/
mkdir -p /etc/php74/ini/
mkdir -p /etc/nginx/conf.d/ 

# Create the files
touch /etc/php74/ini/custom.ini
touch /etc/php80/ini/custom.ini 
touch /etc/php81/ini/custom.ini
touch /etc/php82/ini/custom.ini
touch /etc/php74/fpm/www.conf
touch /etc/php80/fpm/www.conf   
touch /etc/php81/fpm/www.conf
touch /etc/php82/fpm/www.conf
touch /etc/nginx/conf.d/default.conf # to avoid nginx crashing


# Create Docker Network
sudo docker network create hosting_net

# to be placed in the file stored in /etc/nginx/conf.d/custom.conf [Vital to stop Nginx crashing]
echo "limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;" >> /etc/nginx/conf.d/custom.conf

# Setup hosting suite apps
echo "Setting up the hosting suite apps..."
sudo docker compose docker-compose.yml up -d --build

echo -e "Setting up the hosting suite apps... Done! \n"

echo -e "Setting up server and CGI apps... \n"
docker compose -f hosting-server-nginx/docker-compose.yml up -d --build

