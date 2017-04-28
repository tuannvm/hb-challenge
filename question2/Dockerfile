FROM python:2-alpine

LABEL Name=pydock
LABEL Version=1.0.0

ENV WORKDIR /srv
ENV CERTSDIR /srv/certs
ENV CA_FILE=${CERTSDIR}/ca.pem
ENV CLIENT_CERT ${CERTSDIR}/cert.pem
ENV CLIENT_KEY ${CERTSDIR}/key.pem
WORKDIR ${WORKDIR}

ADD requirements_alpine.txt requirements.txt

RUN pip install -r requirements.txt

ADD app.py .

ENTRYPOINT ["python", "app.py"]