FROM php:7.2-apache

COPY ./apache/*.conf /etc/apache2/sites-available/

RUN apt-get update \
  && apt-get install -y zlib1g-dev libpq-dev mysql-client unzip\
  && docker-php-ext-install zip pdo_mysql mysqli \
  && docker-php-ext-enable mysqli \
  && a2enmod headers \
  && a2enmod rewrite \
  && a2enmod userdir

RUN php -r "copy('https://getcomposer.org/installer', '/composer-setup.php');"
RUN php -r "if (hash_file('sha384', '/composer-setup.php') === '48e3236262b34d30969dca3c37281b3b4bbe3221bda826ac6a9a62d6444cdb0dcd0615698a5cbe587c3f0fe57a54d8f5') { echo 'Installer verified'; } else { echo 'Installer corrupt'; unlink('/composer-setup.php'); } echo PHP_EOL;"
RUN php /composer-setup.php
RUN php -r "unlink('/composer-setup.php');"
RUN mv composer.phar /usr/local/bin/composer
RUN chmod +x /usr/local/bin/composer

ENV COMPOSER_ALLOW_SUPERUSER 1
ENV COMPOSER_HOME /composer
ENV PATH $PATH:/composer/vendor/bin

RUN useradd -ms /bin/bash ubuntu

RUN echo "New Demo project" && cd /home/ubuntu && composer create-project laravel/laravel /home/ubuntu/public_html/ 5.5.*
RUN chmod -R 777 /home/ubuntu/public_html/storage
WORKDIR /home/ubuntu/public_html
COPY ./patch/EncryptCookies.php ./vendor/laravel/framework/src/Illuminate/Cookie/Middleware/EncryptCookies.php
COPY ./flag /flag
