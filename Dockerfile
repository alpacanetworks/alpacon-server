# Build: docker build -t alpacon-server .
# Run: docker run --env-file .docker/env -p 8000:8000 alpacon-server --restart unless-stopped

FROM node:slim AS builder

WORKDIR /root

COPY package.json ./

RUN npm install

FROM python:3.11-slim-bullseye

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends gcc gettext libffi-dev libpq-dev libssl-dev libldap2-dev libsasl2-dev
RUN addgroup --system --gid 200 alpacon && adduser --system --uid 200 --gid 200 --home /var/lib/alpacon --shell /bin/bash --disabled-password --disabled-login alpacon

WORKDIR /opt/alpacon

COPY --from=builder /root/node_modules ./
COPY . .

RUN pip install --no-cache-dir -r requirements.txt && django-admin compilemessages --ignore env
RUN mkdir /opt/alpacon/media && chown -R alpacon:alpacon /opt/alpacon/media

USER alpacon

ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/var/lib/alpacon/.local/bin

EXPOSE 8000

CMD ["gunicorn", "--bind", ":8000", "--workers", "3", "alpacon.wsgi:application"]
