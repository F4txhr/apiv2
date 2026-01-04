#!/bin/bash

if [ ! -f .env ]; then
  echo "Error: .env file not found. Please copy .env.example to .env and edit it."
  exit 1
fi

source .env

if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "api.yourdomain.com" ]; then
  echo "Error: DOMAIN is not set in .env"
  exit 1
fi

if [ -z "$EMAIL" ] || [ "$EMAIL" = "your-email@example.com" ]; then
  echo "Error: EMAIL is not set in .env"
  exit 1
fi

# Update Nginx Configuration with actual domain initially to ensure Nginx starts
echo "### Updating Nginx configuration with domain $DOMAIN ..."
sed -i "s/REPLACE_WITH_DOMAIN/$DOMAIN/g" nginx/default.conf

data_path="./certbot"
rsa_key_size=4096
regex="([^www.].+)"

echo "### Starting setup for domain $DOMAIN with email $EMAIL ..."

if [ -d "$data_path" ]; then
  read -p "Existing data found for $DOMAIN. Continue and replace existing certificate? (y/N) " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    exit
  fi
fi

if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
  echo "### Downloading recommended TLS parameters ..."
  mkdir -p "$data_path/conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
  echo
fi

echo "### Creating dummy certificate for $DOMAIN ..."
path="/etc/letsencrypt/live/$DOMAIN"
mkdir -p "$data_path/conf/live/$DOMAIN"
docker compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 1\
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot
echo

echo "### Starting nginx ..."
docker compose up --force-recreate -d nginx
echo

echo "### Deleting dummy certificate for $DOMAIN ..."
docker compose run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$DOMAIN && \
  rm -Rf /etc/letsencrypt/archive/$DOMAIN && \
  rm -Rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot
echo

echo "### Requesting Let's Encrypt certificate for $DOMAIN ..."
#Join $domains to -d args
domain_args="-d $DOMAIN"

# Select appropriate email arg
case "$EMAIL" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="-m $EMAIL" ;;
esac

# Enable staging mode if needed
if [ "$STAGING" != "0" ]; then staging_arg="--staging"; fi

docker compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size $rsa_key_size \
    --agree-tos \
    --force-renewal" certbot
echo

echo "### Checking for actual certificate path (handling -0001 suffix) ..."
# Find the directory that contains the privkey.pem for the domain
# We look in the local ./certbot/conf/live folder
# The 'ls -d' will list directories matching the domain pattern
# 'head -n 1' takes the first match
ACTUAL_CERT_DIR=$(ls -d ./certbot/conf/live/$DOMAIN* | head -n 1)
CERT_NAME=$(basename "$ACTUAL_CERT_DIR")

if [ -n "$CERT_NAME" ] && [ "$CERT_NAME" != "$DOMAIN" ]; then
  echo "### Detected certificate suffix: $CERT_NAME. Updating Nginx config ..."
  # Replace the original domain path with the suffixed path in nginx.conf
  # We match /etc/letsencrypt/live/DOMAIN/ and replace with /etc/letsencrypt/live/CERT_NAME/
  # Note: The nginx config inside the container uses /etc/letsencrypt, which maps to ./certbot/conf
  sed -i "s|/etc/letsencrypt/live/$DOMAIN/|/etc/letsencrypt/live/$CERT_NAME/|g" nginx/default.conf
fi

echo "### Reloading nginx ..."
docker compose exec nginx nginx -s reload
