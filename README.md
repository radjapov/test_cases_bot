# Test Case Generator Telegram Bot

This bot uses a powerful AI model (Google Gemini) to transform raw text, feature descriptions, and user stories into structured, QA-oriented test cases.

## Features

-   **Generate Test Cases:** Create detailed test cases from unstructured text.
-   **Multiple Formats:** Get results in Markdown (default), JSON, or CSV.
-   **Templates:** Use different generation templates like `Classic`, `API-first`, or `Banking` for more specific tests.
-   **History:** View your last 5 generation requests.
-   **Export:** Download the latest result as a file.
-   **Secure:** Access is restricted to a whitelist of Telegram user IDs.

## Bot Commands

-   `/start` - Initialize the bot, see a welcome message.
-   `/new` - Start a new test case generation process. The bot will ask for your text.
-   `/format` - Change the output format (Markdown, JSON, CSV).
-   `/template` - Change the test case generation template.
-   `/history` - Show the last 5 generated test cases.
-   `/export` - Export the last generated test case as a file.

---

## Local Development (with Docker)

### Prerequisites

-   Docker and Docker Compose
-   Git

### Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd test-case-generator-bot
    ```

2.  **Create and configure the environment file:**
    ```bash
    cp .env.example .env
    ```
    Now, edit the `.env` file with your actual credentials:
    -   `BOT_TOKEN`: Your Telegram bot token from `@BotFather`.
    -   `GEMINI_API_KEY`: Your Google AI Gemini API key.
    -   `ALLOWED_TELEGRAM_IDS`: A comma-separated list of numeric Telegram user IDs that are allowed to use the bot. You can get your ID from bots like `@userinfobot`.

3.  **Build and run the container:**
    ```bash
    docker-compose up --build
    ```
    The bot will start in polling mode. You can interact with it on Telegram. To run in the background, use `docker-compose up -d --build`.

4.  **Stopping the bot:**
    ```bash
    docker-compose down
    ```

---

## Deployment on a VPS (Ubuntu 22.04)

These instructions cover deploying the bot using Docker Compose, which is the recommended method.

### 1. Server Preparation

1.  **Create a non-root user:**
    ```bash
    adduser <your_user>
    usermod -aG sudo <your_user>
    su - <your_user>
    ```

2.  **Configure Firewall:**
    ```bash
    sudo ufw allow OpenSSH
    sudo ufw allow http
    sudo ufw allow https
    sudo ufw enable
    ```

### 2. Install Docker

Follow the official Docker documentation to install Docker and Docker Compose on Ubuntu.

-   [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/)
-   The `docker-compose` command is now part of the `docker` command itself (`docker compose`).

### 3. Deploy the Bot

1.  **Clone the repository and navigate to the directory:**
    ```bash
    git clone <repository_url>
    cd test-case-generator-bot
    ```

2.  **Configure the environment:**
    Create a `.env` file and fill it with your production credentials.
    ```bash
    cp .env.example .env
    nano .env
    ```
    -   For production, it's highly recommended to use the `webhook` mode.
    -   Set `BOT_MODE="webhook"`.
    -   Set `WEBHOOK_BASE_URL="https://your.domain.com"`.
    -   Set `WEBHOOK_PATH="/webhook/your_secret_path"`.

3.  **Run with Docker Compose:**
    ```bash
    docker compose up -d --build
    ```
    Your bot is now running in the background.

### 4. Configure Nginx for Webhook

If you are using `webhook` mode, you need a reverse proxy like Nginx to forward requests from Telegram to your bot.

1.  **Install Nginx:**
    ```bash
    sudo apt update
    sudo apt install nginx
    ```

2.  **Create an Nginx configuration file:**
    ```bash
    sudo nano /etc/nginx/sites-available/telegram_bot
    ```
    Paste the following configuration, adjusting `your.domain.com` and the port/path if necessary. The bot runs on port `8080` inside the container. You need to map it in `docker-compose.yml`.

    ```nginx
    server {
        listen 80;
        server_name your.domain.com;

        # Redirect HTTP to HTTPS
        location / {
            return 301 https://$host$request_uri;
        }
    }

    server {
        listen 443 ssl;
        server_name your.domain.com;

        # SSL certs (managed by Certbot)
        ssl_certificate /etc/letsencrypt/live/your.domain.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/your.domain.com/privkey.pem;
        include /etc/letsencrypt/options-ssl-nginx.conf;
        ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

        location /webhook/your_secret_path {
            proxy_pass http://127.0.0.1:8080; # Assuming you mapped the container's port 8080 to the host's 8080
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    ```

3.  **Enable the site and get SSL certificate:**
    ```bash
    sudo ln -s /etc/nginx/sites-available/telegram_bot /etc/nginx/sites-enabled/
    sudo nginx -t # Test config
    sudo systemctl restart nginx

    # Install certbot and get a certificate
    sudo apt install certbot python3-certbot-nginx
    sudo certbot --nginx -d your.domain.com
    ```

### 5. Updating the Bot

To update the bot with the latest code changes:

```bash
cd test-case-generator-bot
git pull
docker compose up -d --build
```
