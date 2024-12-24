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

######### Nginx part #########
FROM smebberson/alpine-nginx:3.0.0 AS PageServing

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
