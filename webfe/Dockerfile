######### Npm part #########
FROM node:18.20.1 AS StaticBuilding

ARG APP_VERSION=ce
ARG NODE_ENV=production
ENV NPM_VERSION 10.5.0

# install requirements & build
COPY ./package_vue /package_vue
WORKDIR /package_vue
RUN npm install --unsafe-perm --registry=https://mirrors.tencent.com/npm/
RUN npm run build

######### Nginx part #########
FROM smebberson/alpine-nginx:3.0.0 AS PageServing
RUN apk update && apk add gettext
RUN ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

# clean useless files
RUN cd /var/www && rm -r localhost
# cp nginx files
COPY custom-configs/default /etc/nginx/conf.d/default.conf
COPY custom-configs/30-render /etc/cont-init.d/30-render
COPY --from=0 /package_vue/dist/ /var/www/
