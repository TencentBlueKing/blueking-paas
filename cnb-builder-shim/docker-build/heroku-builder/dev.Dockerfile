ARG BUILDER_IMAGE_NAME=mirrors.tencent.com/bkpaas/builder-heroku-noble
ARG BUILDER_IMAGE_TAG=latest

# -------------- builder container --------------
FROM golang:1.24.6-bookworm as binary-builder

WORKDIR /src

COPY ./go.mod ./go.mod
COPY ./go.sum ./go.sum

RUN go mod download

COPY ./cmd ./cmd
COPY ./pkg ./pkg
COPY ./internal ./internal
COPY ./Makefile ./Makefile

RUN make build-dev

# -------------- runner container --------------
FROM ${BUILDER_IMAGE_NAME}:${BUILDER_IMAGE_TAG}

USER root

WORKDIR /app

# copy custom binaries
COPY ./rootfs/devsandbox/usr/bin/ /usr/bin/

# copy config to /etc/s6-overlay
COPY ./rootfs/devsandbox/etc/s6-overlay /etc/s6-overlay

# install s6-overlay
ARG S6_OVERLAY_DOWNLOAD_URL=https://github.com/just-containers/s6-overlay/releases/download
ARG S6_OVERLAY_VERSION=v3.2.1.0

RUN set -eux; \
    wget -q \
        "${S6_OVERLAY_DOWNLOAD_URL}/${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz" \
        "${S6_OVERLAY_DOWNLOAD_URL}/${S6_OVERLAY_VERSION}/s6-overlay-symlinks-noarch.tar.xz" \
        "${S6_OVERLAY_DOWNLOAD_URL}/${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz"; \
    tar -C / -Jxpf s6-overlay-noarch.tar.xz; \
    tar -C / -Jxpf s6-overlay-symlinks-noarch.tar.xz; \
    tar -C / -Jxpf s6-overlay-x86_64.tar.xz; \
    rm -f *.tar.xz

# install code-server
ARG CODE_SERVER_VER=4.102.1

RUN wget https://github.com/coder/code-server/releases/download/v${CODE_SERVER_VER}/code-server_${CODE_SERVER_VER}_amd64.deb; \
  dpkg -i code-server_${CODE_SERVER_VER}_amd64.deb; \
  rm code-server_${CODE_SERVER_VER}_amd64.deb

# set code-server configuration stored directory
ENV XDG_DATA_HOME=/coder

# pre-install extensions for developer
RUN code-server --install-extension ms-python.python

# heroku builder
ENV HOME=/app CNB_APP_DIR=/app CNB_PLATFORM_API=0.11

# dev mode for builder
ENV DEV_MODE=true

RUN apt-get clean && apt-get update && apt-get -y install supervisor

COPY --from=binary-builder /src/bin/* /cnb/devsandbox/bin/

# use s6-overlay to start container's processes
ENTRYPOINT ["/init"]
