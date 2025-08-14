# Copyright 2025 Canonical Ltd.
# See LICENSE file for licensing details.
FROM python:3.13-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends git=1:2.39.* && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /usr/src/app
WORKDIR /usr/src/app

COPY . /usr/src/app
RUN pip install --no-cache-dir /usr/src/app

ENV PYTHONPATH /usr/src/app
CMD ["/usr/src/app/main.py"]
