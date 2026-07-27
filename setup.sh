#!/bin/bash
echo "Please specify the backend IP address for the hosting suite UI (e.g., 192.168.1.100):"
read backend

echo "Setup Docker? (y/n):"
read setup_docker

if [ "$setup_docker" = "y" ]; then
    echo "Setting up Docker..."
    sudo apt update
    sudo apt install -y docker.io 

    mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu \
    $(lsb_release -cs) stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt update

    apt install docker-compose-plugin -y

    echo "Docker setup complete."
else
    echo "Skipping Docker setup."
fi

# Make the directories:
sudo mkdir -p /etc/php74/fpm
sudo mkdir -p /etc/php80/fpm
sudo mkdir -p /etc/php81/fpm
sudo mkdir -p /etc/php82/fpm
sudo mkdir -p /etc/php82/ini/
sudo mkdir -p /etc/php81/ini/
sudo mkdir -p /etc/php80/ini/
sudo mkdir -p /etc/php74/ini/
sudo mkdir -p /etc/nginx/conf.d/ 

# Create the files
sudo touch /etc/php74/ini/custom.ini
sudo touch /etc/php80/ini/custom.ini 
sudo touch /etc/php81/ini/custom.ini
sudo touch /etc/php82/ini/custom.ini
sudo touch /etc/php74/fpm/www.conf
sudo touch /etc/php80/fpm/www.conf   
sudo touch /etc/php81/fpm/www.conf
sudo touch /etc/php82/fpm/www.conf
sudo touch /etc/nginx/conf.d/default.conf # to avoid nginx crashing

# Replace the backend IP address in the hosting-ui/src/js/app.js file
sed -i "s/{{backend}}/$backend/g" hosting-ui/src/js/app.js

# Create Docker Network
sudo docker network create hosting_net &>/dev/null

# to be placed in the file stored in /etc/nginx/conf.d/custom.conf [Vital to stop Nginx crashing]
echo 'limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;' | sudo tee /etc/nginx/conf.d/custom.conf

# Setup hosting suite apps
echo "Setting up the hosting suite apps..."
sudo docker compose up -d --build

echo -e "Setting up the hosting suite apps... Done! \n"

echo -e "Setting up server and CGI apps... \n"
sudo docker compose -f hosting-server-nginx/docker-compose.yml up -d --build

