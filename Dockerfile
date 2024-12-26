FROM python:3.8
WORKDIR /xiaomi
COPY xiaomi .
RUN pip install -r /xiaomi/requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
COPY docker-entrypoint.sh /usr/local/bin/
RUN ln -s usr/local/bin/docker-entrypoint.sh /entrypoint.sh
ENTRYPOINT ["docker-entrypoint.sh"]

# docker buildx build --platform linux/arm64,linux/arm/v7 -t a180285/xiaomi-router-exporter:v20241226 --push .