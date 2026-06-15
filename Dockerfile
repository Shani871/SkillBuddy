FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libjpeg62-turbo-dev zlib1g-dev pkg-config libcairo2-dev python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
COPY requirements requirements
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
RUN chmod +x scripts/start.sh

EXPOSE 8000

CMD ["./scripts/start.sh"]
