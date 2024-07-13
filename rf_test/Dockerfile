FROM python:3.8-alpine

WORKDIR /usr/src/app

COPY tests.sh test-server.robot requirements.txt ./

RUN pip install -r requirements.txt
RUN apk add --no-cache wget

CMD ["sh", "tests.sh"]