FROM python:3-slim AS builder

COPY requirements.txt /app
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app
WORKDIR /app

# A distroless container image with Python and some basics like SSL certificates
# https://github.com/GoogleContainerTools/distroless
FROM gcr.io/distroless/python3-debian10
COPY --from=builder /app /app
WORKDIR /app
ENV PYTHONPATH /app
CMD ["/app/main.py"]
