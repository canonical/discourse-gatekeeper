# Copyright 2023 Canonical Ltd.
# See LICENSE file for licensing details.
FROM python:3.11.4-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git=1:2.39.* && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

ENV PYTHONPATH /usr/src/app
CMD ["/usr/src/app/main.py"]
