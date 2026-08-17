# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    ODOO_RC=/etc/odoo/odoo.conf

# Build toolchain + libs the pinned python deps compile against, fonts used by
# PDF reports, wkhtmltopdf for report printing, Node for asset bundling (rtlcss).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        ca-certificates \
        git \
        nodejs \
        npm \
        python3-dev \
        libxml2-dev \
        libxslt1-dev \
        libjpeg-dev \
        zlib1g-dev \
        libfreetype6-dev \
        liblcms2-dev \
        libwebp-dev \
        libharfbuzz-dev \
        libfribidi-dev \
        libxcb1-dev \
        libpq-dev \
        libsasl2-dev \
        libldap2-dev \
        libssl-dev \
        postgresql-client \
        fonts-dejavu-core \
        fonts-freefont-ttf \
        fonts-noto-core \
        fonts-inconsolata \
        fonts-font-awesome \
        gsfonts \
        xfonts-75dpi \
        xfonts-base \
    && npm install -g rtlcss \
    && curl -sSL -o /tmp/wkhtmltox.deb \
        https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && apt-get install -y --no-install-recommends /tmp/wkhtmltox.deb \
    && rm -f /tmp/wkhtmltox.deb \
    && rm -rf /var/lib/apt/lists/*
# Note: build-essential/python3-dev are kept (not purged) because psycopg2
# (not psycopg2-binary) compiles from source against libpq during pip install.

WORKDIR /opt/odoo

# Install python deps first so source-only changes don't bust this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir --timeout 100 --retries 10 -r requirements.txt

COPY . .

RUN mkdir -p /etc/odoo /var/lib/odoo/data \
    && cp docker/odoo.conf /etc/odoo/odoo.conf \
    && cp docker/entrypoint.sh /entrypoint.sh \
    && chmod +x /entrypoint.sh odoo-bin

EXPOSE 8069

ENTRYPOINT ["/entrypoint.sh"]
CMD ["odoo"]
