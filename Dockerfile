#!/bin/sh
# Build Stage
FROM python:3.12.1 AS builder
WORKDIR /code
ADD . /code
RUN pip install fastapi["all"]
RUN pip install redis
RUN pip install pymysql
RUN pip install cryptography
RUN pip install "apitally[fastapi]"
RUN pip install sqlalchemy
#RUN pip install --no-cache-dir -r /code/requirements.txt
RUN date '+%Y.%m.%d.%H%M%S' > build_number.txt
RUN pip install pyinstaller
RUN pyinstaller -F main.py

# Runtime
FROM ubuntu:22.04 AS runtime
WORKDIR /app
COPY --from=builder /code/dist/main .
COPY --from=builder /code/build_number.txt .
EXPOSE 8080
ENTRYPOINT ["./main"]