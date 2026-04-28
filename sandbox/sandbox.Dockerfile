FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y \
    verilator \
    make \
    g++ \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /workspace
CMD ["bash"]