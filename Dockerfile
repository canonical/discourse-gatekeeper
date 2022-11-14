FROM python:3-slim AS builder

RUN mkdir /usr/src/app
WORKDIR /usr/src/app
COPY requirements.txt /usr/src/app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /usr/src/app

# A distroless container image with Python and some basics like SSL certificates
# https://github.com/GoogleContainerTools/distroless
FROM gcr.io/distroless/python3-debian10
COPY --from=builder /usr/src/app /usr/src/app
WORKDIR /usr/src/app
ENV PYTHONPATH /usr/src/app
CMD ["/usr/src/app/main.py"]
