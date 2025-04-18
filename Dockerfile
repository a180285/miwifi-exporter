FROM python:3.8

RUN apt update && apt install -y iputils-ping && apt clean
WORKDIR /xiaomi
COPY xiaomi/requirements.txt .
RUN pip install -r /xiaomi/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

COPY xiaomi .
COPY docker-entrypoint.sh /usr/local/bin/
RUN ln -s usr/local/bin/docker-entrypoint.sh /entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# docker build -t a180285/xiaomi-router-exporter:v20250418_v4 --push .