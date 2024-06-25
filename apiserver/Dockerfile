################# Admin42 #################
FROM node:12.13.0-stretch AS admin42
USER root
WORKDIR /build

ARG EDITION
ENV NPM_VERSION 5.6.0

# 安装依赖
ADD package.json .
RUN npm install --unsafe-perm --registry=https://mirrors.tencent.com/npm/

# 拷贝源码
ADD ./.babelrc .
ADD ./.bootstraprc .
ADD ./.eslintrc.js .
ADD ./postcss.config.js .
ADD ./paasng/assets ./paasng/assets
ADD ./configs ./configs

# 执行编译
RUN EDITION=${EDITION} npm run build

################# PaaS #################
FROM python:3.8.13-slim-buster
USER root

RUN apt-get update && apt-get install -y gcc subversion ssh default-libmysqlclient-dev pkg-config vim

# Add buster-backports to sources.list
RUN echo "deb http://archive.debian.org/debian buster-backports main" >> /etc/apt/sources.list
# Install git from backports, because the version(git:v2.20.1) in buster will leak usernames from the url
# And this bug is fixed in v2.22.0, so we should install git from buster-backports, which is v2.30.2-1
# See more info at: https://packages.debian.org/buster-backports/git
#
# Update(2024-05-07): The GitClient class has added a new logic to remove sensitive information
# in the git command output, so a newer git version is no longer required to fix the username leakage.
RUN apt-get update && apt-get -y install -t buster-backports git

RUN mkdir ~/.pip &&  printf '[global]\nindex-url = https://mirrors.cloud.tencent.com/pypi/simple/\n' > ~/.pip/pip.conf

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN pip install --upgrade 'pip<24.1'

RUN pip install poetry==1.3.2

# Change security level of openssl to lower value in order to avoid "CA_MD_TOO_WEAK" error
# See https://stackoverflow.com/questions/52218876/how-to-fix-ssl-issue-ssl-ctx-use-certificate-ca-md-too-weak-on-python-zeep?rq=1
RUN sed -i "s/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=0/g" /etc/ssl/openssl.cnf

WORKDIR /app

ADD ./pyproject.toml .
ADD ./poetry.lock .

# Install dependecies in system
# Disable "new installer" to fix https://github.com/python-poetry/poetry/issues/6301
RUN poetry config virtualenvs.create false && poetry config experimental.new-installer false && poetry install --no-dev

ARG BKPAAS_BUILD_VERSION="tag: null, commitID: ^HEAD, buildID: null, buildTime: null"
ENV BKPAAS_BUILD_VERSION=${BKPAAS_BUILD_VERSION}

RUN mkdir -p ./public

COPY --from=admin42 /build/paasng/public ./public
ADD ./paasng .

COPY ./start.sh .
COPY ./start_celery.sh .
COPY ./init.sh .
CMD ["./start.sh"]
