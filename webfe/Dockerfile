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
FROM tencentos/tencentos4-minimal AS PageServing

RUN yum install -y nginx gettext procps bind-utils && \
    yum clean all && \
    rm -rf /var/cache/yum && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log

RUN sed -i 's/worker_processes auto/worker_processes 1/g' /etc/nginx/nginx.conf

ARG BKPAAS_BUILD_VERSION="tag: null, commitID: ^HEAD, buildID: null, buildTime: null"
ENV BKPAAS_BUILD_VERSION=${BKPAAS_BUILD_VERSION}

# cp nginx files
COPY custom-configs/default /etc/nginx/conf.d/default.conf
# cp built webfe files
COPY --from=StaticBuilding /package_vue/dist/ /var/www/

# generate index.html by rendering index.html.template via environment variables
RUN printf '#!/bin/bash\nmv /var/www/index.html{,.template} && envsubst </var/www/index.html.template >/var/www/index.html\nexec nginx -g "daemon off;"' > /init && \
    chmod +x /init

# Expose the ports for nginx
EXPOSE 80

CMD ["/init"]
