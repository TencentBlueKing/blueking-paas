FROM mirrors.tencent.com/blueking/python:3.11.10-ts4
USER root

RUN yum install -y gcc procps bind-utils

RUN mkdir ~/.pip &&  printf '[global]\nindex-url = https://mirrors.cloud.tencent.com/pypi/simple/\nextra-index-url = https://mirrors.tencent.com/repository/pypi/tencent_pypi/simple/' > ~/.pip/pip.conf

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

RUN pip install --upgrade 'pip<24.1'

RUN pip install poetry==2.1.1

# Change security level of openssl to lower value in order to avoid "CA_MD_TOO_WEAK" error
# See https://stackoverflow.com/questions/52218876/how-to-fix-ssl-issue-ssl-ctx-use-certificate-ca-md-too-weak-on-python-zeep?rq=1
RUN sed -i '/oid_section/a openssl_conf = default_conf' /etc/pki/tls/openssl.cnf && \
    printf "[default_conf]\nssl_conf=ssl_sect\n[ssl_sect]\nsystem_default=system_default_sect\n[system_default_sect]\nMinProtocol=TLSv1.2\nCipherString=DEFAULT@SECLEVEL=0" >> /etc/pki/tls/openssl.cnf

WORKDIR /app

# Install dependencies first
ADD ./pyproject.toml .
ADD ./poetry.lock .
# Install dependecies in system
RUN poetry config virtualenvs.create false && poetry install --no-root -vvv

ADD ./data ./data
ADD ./docs ./docs
ADD ./monitor ./monitor
ADD ./static ./static
ADD ./svc_rabbitmq ./svc_rabbitmq
ADD ./tasks ./tasks
ADD ./templates ./templates
ADD ./vendor ./vendor
ADD ./manage.py .
ADD ./start.sh .

CMD ["/bin/bash", "./start.sh"]
