FROM python:3.11-slim
ARG VERIBLE_VERSION=v0.0-4080-ga0a8d8eb

ENV PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    ghdl \
    && rm -rf /var/lib/apt/lists/*
ADD https://github.com/chipsalliance/verible/releases/download/${VERIBLE_VERSION}/verible-${VERIBLE_VERSION}-linux-static-x86_64.tar.gz /tmp/verible.tar.gz
RUN mkdir -p /tmp/verible \
    && tar -xzf /tmp/verible.tar.gz -C /tmp/verible --strip-components=1 \
    && cp /tmp/verible/bin/verible-verilog-lint /usr/local/bin/ \
    && rm -rf /tmp/verible /tmp/verible.tar.gz
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY . /app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
