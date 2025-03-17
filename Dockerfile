#!/bin/sh
# Build Stage
FROM python:3.12.1 AS builder
WORKDIR /code
ADD . /code
RUN pip install fastapi["all"]
RUN pip install redis
RUN pip install pymysql
RUN pip install cryptography
RUN pip install sqlalchemy
RUN pip install pytz
RUN pip install colorama
RUN pip install "sentry-sdk[fastapi]"
#RUN pip install --no-cache-dir -r /code/requirements.txt
RUN date '+%Y.%m.%d' > build_number.txt
RUN pip install pyinstaller
RUN pyinstaller -F main.py

# Runtime
FROM ubuntu:22.04 AS runtime
WORKDIR /app
RUN apt-get update && apt-get install -y tzdata \
    && ln -snf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime \
    && echo "Asia/Shanghai" > /etc/timezone
COPY --from=builder /code/dist/main .
COPY --from=builder /code/build_number.txt .
COPY --from=builder /code/current_commit.txt .
EXPOSE 8080
ENTRYPOINT ["./main"]