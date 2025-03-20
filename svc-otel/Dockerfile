FROM python:3.11.10-slim-bullseye
USER root

RUN apt-get update && apt-get install gcc curl procps -y

RUN mkdir ~/.pip &&  printf '[global]\nindex-url = https://mirrors.cloud.tencent.com/pypi/simple/\nextra-index-url = https://mirrors.tencent.com/repository/pypi/tencent_pypi/simple/' > ~/.pip/pip.conf

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN pip install --upgrade 'pip<24.1'

RUN pip install poetry==2.1.1

# Change security level of openssl to lower value in order to avoid "CA_MD_TOO_WEAK" error
# See https://stackoverflow.com/questions/52218876/how-to-fix-ssl-issue-ssl-ctx-use-certificate-ca-md-too-weak-on-python-zeep?rq=1
RUN sed -i "s/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=0/g" /etc/ssl/openssl.cnf

WORKDIR /app

# Install dependencies first
ADD ./pyproject.toml .
ADD ./poetry.lock .
# Install dependecies in system
RUN poetry config virtualenvs.create false && poetry install --no-root -vvv

ADD ./data ./data
ADD ./svc_otel ./svc_otel
ADD ./static ./static
ADD ./manage.py .
ADD ./start.sh .

ENV TINI_VERSION v0.19.0
ADD https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini /tini
RUN chmod +x /tini start.sh

ENV DJANGO_SETTINGS_MODULE svc_otel.settings

EXPOSE 80
ENTRYPOINT ["/tini", "--"]
CMD ["./start.sh"]
