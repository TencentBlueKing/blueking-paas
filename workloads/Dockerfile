FROM python:3.8.13-slim-buster
USER root

RUN apt-get update && apt-get install  -y gcc default-libmysqlclient-dev procps curl

RUN mkdir ~/.pip &&  printf '[global]\nindex-url = https://mirrors.cloud.tencent.com/pypi/simple/\nextra-index-url = https://mirrors.tencent.com/repository/pypi/tencent_pypi/simple/' > ~/.pip/pip.conf

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN pip install --upgrade pip
RUN pip install poetry==1.3.2

# Change security level of openssl to lower value in order to avoid "CA_MD_TOO_WEAK" error
# See https://stackoverflow.com/questions/52218876/how-to-fix-ssl-issue-ssl-ctx-use-certificate-ca-md-too-weak-on-python-zeep?rq=1
RUN sed -i "s/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=0/g" /etc/ssl/openssl.cnf

WORKDIR /app

ADD ./pyproject.toml ./
ADD ./poetry.lock ./

# Install dependecies in system
# unittest 要安装 dev 依赖
ARG POETRY_INSTALL_EXTRA_ARGS
# Disable "new installer" to fix https://github.com/python-poetry/poetry/issues/6301
RUN poetry config virtualenvs.create false && poetry config experimental.new-installer false && poetry install ${POETRY_INSTALL_EXTRA_ARGS}

ADD ./bin/start.sh ./
ADD ./bin/start_celery.sh ./
ADD ./paas_wl ./

CMD ["bash", "/app/start.sh"]
