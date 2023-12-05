ARG IMAGE=heroku/heroku
ARG TAG=18.v27

FROM ${IMAGE}:${TAG}

ARG sources
ARG packages
ARG package_args='--allow-downgrades --allow-remove-essential --allow-change-held-packages --no-install-recommends'


# Set required CNB information
LABEL io.buildpacks.stack.id="heroku-18"
ENV CNB_USER_ID=2000 CNB_GROUP_ID=2000 CNB_STACK_ID="heroku-18" STACK="heroku-18"

# Create the user
RUN groupadd --gid ${CNB_GROUP_ID} cnb && \
  useradd --uid ${CNB_USER_ID} --gid ${CNB_GROUP_ID} -m -s /bin/bash --home-dir /app cnb && \
  chown cnb:cnb /app /tmp -R

# Install common packages
ARG TIME_ZONE=Asia/Shanghai
ENV TZ=${TIME_ZONE}
RUN rm /etc/localtime && ln -s /usr/share/zoneinfo/${TIME_ZONE} /etc/localtime

RUN echo "$sources" > /etc/apt/sources.list

RUN echo "debconf debconf/frontend select noninteractive" | debconf-set-selections && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get clean && apt-get update && apt-get -y $package_args update && \
    apt-get -y $package_args install locales && \
    locale-gen en_US.UTF-8 && \
    update-locale LANG=en_US.UTF-8 LANGUAGE=en_US.UTF-8 LC_ALL=en_US.UTF-8 && \
    echo $packages | xargs apt-get -y $package_args install && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf \
    /usr/share/doc \
    /usr/share/man \
    /usr/share/info \
    /usr/share/locale \
    /var/lib/apt/lists/* \
    /tmp/* \
    /etc/apt/preferences \
    /var/log/* \
    /var/cache/debconf/* \
    /etc/systemd \
    /lib/lsb \
    /lib/udev \
    /usr/lib/x86_64-linux-gnu/gconv/IBM* \
    /usr/lib/x86_64-linux-gnu/gconv/EBC* && \
    bash -c "mkdir -p /usr/share/man/man{1..8}"

COPY rootfs/ /
USER cnb
WORKDIR /app
