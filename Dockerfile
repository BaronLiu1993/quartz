FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | apt-key add - \
    && echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-6.0.list \
    && apt-get update && apt-get install -y \
    mongodb-org \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /data/db && \
    chown -R mongodb:mongodb /data/db

WORKDIR /workspace

EXPOSE 27017

CMD ["mongod", "--bind_ip", "0.0.0.0", "--dbpath", "/data/db"]
