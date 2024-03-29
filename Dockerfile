FROM python:3.10.13-slim-bullseye
WORKDIR /usr/src/app

RUN apt-get update && apt-get install -y --no-install-recommends \
python3-pip \
git \
&& \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

RUN pip install numpy
RUN pip install torch

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt
# RUN pip install numpy Pillow torch

CMD python3 server.py
