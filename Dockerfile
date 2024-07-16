FROM python:3.11.9-slim-bookworm
WORKDIR /usr/src/app

COPY requirements.txt ./requirements.txt
RUN pip install -r requirements.txt

CMD python3 server.py
