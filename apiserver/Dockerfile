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
FROM mirrors.tencent.com/blueking/python:3.11.10-ts4
USER root

RUN yum install -y gcc subversion openssh-clients mysql-devel pkg-config vim git gettext procps bind-utils

RUN mkdir ~/.pip && printf '[global]\nindex-url = https://mirrors.cloud.tencent.com/pypi/simple/\n' > ~/.pip/pip.conf

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN pip install --upgrade 'pip<24.1'

RUN pip install poetry==2.1.1

# Change security level of openssl to lower value in order to avoid "CA_MD_TOO_WEAK" error
# See https://stackoverflow.com/questions/52218876/how-to-fix-ssl-issue-ssl-ctx-use-certificate-ca-md-too-weak-on-python-zeep?rq=1
RUN sed -i '/oid_section/a openssl_conf = default_conf' /etc/pki/tls/openssl.cnf && \
    printf "[default_conf]\nssl_conf=ssl_sect\n[ssl_sect]\nsystem_default=system_default_sect\n[system_default_sect]\nMinProtocol=TLSv1.2\nCipherString=DEFAULT@SECLEVEL=0" >> /etc/pki/tls/openssl.cnf

WORKDIR /app

ADD ./pyproject.toml .
ADD ./poetry.lock .

# Install dependencies in system
RUN poetry config virtualenvs.create false && poetry install --without=dev

ARG BKPAAS_BUILD_VERSION="tag: null, commitID: ^HEAD, buildID: null, buildTime: null"
ENV BKPAAS_BUILD_VERSION=${BKPAAS_BUILD_VERSION}

RUN mkdir -p ./public

COPY --from=admin42 /build/paasng/public ./public
ADD ./paasng .

# Add extra files: static assets & I18N .mo translation file.

# the "BKKRILL_ENCRYPT_SECRET_KEY" settings is required for starting the project,
# set it to a non-empty value to run the manage.py command.
RUN export PAAS_BKKRILL_ENCRYPT_SECRET_KEY='none' && \
    poetry run python manage.py check && \
    poetry run python manage.py collectstatic --noinput && \
    poetry run python manage.py compilemessages


COPY ./start.sh .
COPY ./start_celery.sh .
COPY ./init.sh .
CMD ["./start.sh"]
