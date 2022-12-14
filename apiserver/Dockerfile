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

RUN apt-get update && apt-get install -y gcc subversion git ssh default-libmysqlclient-dev vim

RUN mkdir ~/.pip &&  printf '[global]\nindex-url = https://mirrors.cloud.tencent.com/pypi/simple/\n' > ~/.pip/pip.conf

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN pip install --upgrade pip
RUN pip install poetry==1.1.11


# Change security level of openssl to lower value in order to avoid "CA_MD_TOO_WEAK" error
# See https://stackoverflow.com/questions/52218876/how-to-fix-ssl-issue-ssl-ctx-use-certificate-ca-md-too-weak-on-python-zeep?rq=1
RUN sed -i "s/DEFAULT@SECLEVEL=2/DEFAULT@SECLEVEL=0/g" /etc/ssl/openssl.cnf

WORKDIR /app

ADD ./pyproject.toml .
ADD ./poetry.lock .

# Install dependecies in system
RUN poetry config virtualenvs.create false && poetry install --no-dev

RUN mkdir -p ./public

COPY --from=admin42 /build/paasng/public ./public
ADD ./paasng .

COPY ./start.sh .
COPY ./start_celery.sh .
COPY ./init.sh .
CMD ["./start.sh"]
