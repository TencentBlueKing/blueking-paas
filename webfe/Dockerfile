######### Npm part #########
FROM node:14.17.6 AS StaticBuilding

ARG APP_VERSION=ce
ENV APP_VERSION=${APP_VERSION}
ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}
ENV NPM_VERSION 6.14.15

# install requirements at first to make cache-system work better
COPY ./package_vue/package.json /package_vue/package.json
WORKDIR /package_vue
RUN npm install --unsafe-perm --registry=https://mirrors.tencent.com/npm/
# then add source code and build
COPY ./package_vue/ /package_vue/
RUN npm run build

######### Nginx + webfe part #########
## inspired by https://github.com/smebberson/docker-alpine/tree/alpine-nginx-v3.0.0
## 参考 https://github.com/smebberson/docker-alpine/blob/alpine-nginx-v3.0.0/alpine-base/Dockerfile 构建基础镜像
FROM alpine:3.22.1 AS PageServing

# Add s6-overlay
ENV S6_OVERLAY_VERSION=v1.22.1.0 \
    GO_DNSMASQ_VERSION=1.0.7

# 安装 s6 用于托管 nginx 进程；安装 go-dnsmasq 用于增强容器的 dns 服务(容器启动时，dnsmasq 服务会启动)，具体说明参考 https://github.com/smebberson/docker-alpine/blob/alpine-nginx-v3.0.0/alpine-base/README.md#dns
RUN apk add --update --no-cache bind-tools curl libcap && \
    curl -sSL https://github.com/just-containers/s6-overlay/releases/download/${S6_OVERLAY_VERSION}/s6-overlay-amd64.tar.gz \
    | tar xfz - -C / && \
    curl -sSL https://github.com/janeczku/go-dnsmasq/releases/download/${GO_DNSMASQ_VERSION}/go-dnsmasq-min_linux-amd64 -o /bin/go-dnsmasq && \
    chmod +x /bin/go-dnsmasq && \
    apk del curl && \
    # create user and give binary permissions to bind to lower port
    addgroup go-dnsmasq && \
    adduser -D -g "" -s /bin/sh -G go-dnsmasq go-dnsmasq && \
    setcap CAP_NET_BIND_SERVICE=+eip /bin/go-dnsmasq

COPY /rootfs/base/root /

ENTRYPOINT ["/init"]
CMD []

## 参考 https://github.com/smebberson/docker-alpine/blob/alpine-nginx-v3.0.0/alpine-nginx/Dockerfile
# Install nginx
RUN echo "http://mirrors.tencent.com/alpine/v3.22/main" >> /etc/apk/repositories && \
    apk add --update nginx=1.28.0-r3 && \
    rm -rf /var/cache/apk/* && \
    chown -R nginx:www-data /var/lib/nginx

# Add the files
ADD /rootfs/nginx/root /

# Expose the ports for nginx
EXPOSE 80 443

## 构建 webfe 模块
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.tencent.com/g' /etc/apk/repositories
RUN sed -i 's/dl-4.alpinelinux.org/mirrors.tencent.com/g' /etc/apk/repositories

RUN apk update && apk add gettext
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

ARG BKPAAS_BUILD_VERSION="tag: null, commitID: ^HEAD, buildID: null, buildTime: null"
ENV BKPAAS_BUILD_VERSION=${BKPAAS_BUILD_VERSION}

# clean useless files
RUN cd /var/www && rm -r localhost
# cp nginx files
COPY custom-configs/default /etc/nginx/conf.d/default.conf
COPY custom-configs/30-render /etc/cont-init.d/30-render
COPY --from=0 /package_vue/dist/ /var/www/
