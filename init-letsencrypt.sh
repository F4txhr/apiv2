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

# Function to write Nginx config
write_nginx_config() {
  local MODE=$1 # "http" or "https"
  local CERT_PATH=$2 # Optional, e.g., "live/$DOMAIN"

  echo "### Writing Nginx configuration for mode: $MODE ..."

  cat > nginx/default.conf <<EOF
server {
    listen 80;
    server_name _;

    # Serve ACME challenge files
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Proxy to API
    location / {
        proxy_pass http://vpn-api:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

  if [ "$MODE" == "https" ]; then
    cat >> nginx/default.conf <<EOF

server {
    listen 443 ssl;
    server_name $DOMAIN;

    ssl_certificate /etc/letsencrypt/$CERT_PATH/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/$CERT_PATH/privkey.pem;
    
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://vpn-api:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
  fi
}

# 1. Start with HTTP-only config to ensure Nginx can start
write_nginx_config "http"

data_path="./certbot"
rsa_key_size=4096

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
# We need to temporarily enable HTTPS config for the dummy cert so Nginx validates it? 
# Actually no, Certbot needs port 80 for validation. Nginx is running on port 80.
# But for the "dummy" step in the original script, it was creating a cert to allow Nginx to start IF Nginx was configured with SSL.
# Since we default to HTTP-only now, Nginx starts fine without any certs.
# We can skip the dummy cert creation logic if we are careful, but let's keep it to support the eventual switch.
# Wait, if we start Nginx in HTTP-only mode, we don't need the dummy cert to start Nginx.
# We only need Nginx to serve /.well-known/acme-challenge/ on port 80.
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
exit_code=$?

if [ $exit_code -ne 0 ]; then
    echo
    echo "################################################################################"
    echo "### ERROR: Let's Encrypt certificate generation failed!"
    echo "### Falling back to HTTP-only mode on Port 80."
    echo "################################################################################"
    echo
    write_nginx_config "http"
    docker compose exec nginx nginx -s reload
    echo "### Server is running in HTTP mode: http://$DOMAIN"
    exit 1
fi

echo "### Checking for actual certificate path (handling -0001 suffix) ..."
# Find the directory that contains the privkey.pem for the domain
ACTUAL_CERT_DIR=$(ls -d ./certbot/conf/live/$DOMAIN* 2>/dev/null | head -n 1)

if [ -z "$ACTUAL_CERT_DIR" ]; then
    echo "### Error: Certificate files not found despite successful exit code."
    echo "### Falling back to HTTP-only mode."
    write_nginx_config "http"
    docker compose exec nginx nginx -s reload
    exit 1
fi

CERT_NAME=$(basename "$ACTUAL_CERT_DIR")
echo "### Certificate found in: live/$CERT_NAME"

echo "### Enabling HTTPS in Nginx ..."
write_nginx_config "https" "live/$CERT_NAME"

echo "### Reloading nginx ..."
docker compose exec nginx nginx -s reload

echo
echo "################################################################################"
echo "### SUCCESS: HTTPS is enabled!"
echo "### API is available at https://$DOMAIN"
echo "################################################################################"
