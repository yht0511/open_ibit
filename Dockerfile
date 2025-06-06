FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget unzip curl nano git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /Program
COPY . /Program

RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["python", "server.py"]