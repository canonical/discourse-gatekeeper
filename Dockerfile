FROM 3.10-slim AS builder

RUN mkdir /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

FROM 3.10-slim
COPY --from=builder /usr/src/app /usr/src/app
WORKDIR /usr/src/app
ENV PYTHONPATH /usr/src/app
CMD ["/usr/src/app/main.py"]
