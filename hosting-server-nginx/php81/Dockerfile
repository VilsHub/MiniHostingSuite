FROM php:8.1-fpm
COPY ./ini/custom.ini /usr/local/etc/php/conf.d/
RUN docker-php-ext-install mysqli pdo pdo_mysql