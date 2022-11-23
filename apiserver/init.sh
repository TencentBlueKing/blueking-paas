#!/bin/bash

set -eo pipefail

call_steps() {
    steps="$*"
    pids=""
    
    for i in ${steps}; do
        "${i}" &
        pids+="$! "
    done
    
    code=0
    for job in ${pids}; do
        if wait "${job}"; then
            echo "Job ${job} success"
        else
            code=1
            echo "Process ${job} failed"
        fi
    done
    
    return "${code}"
}

ensure-apigw() {
    api_name=bkpaas3
    # 同步网关基本信息
    python manage.py sync_apigw_config \
    --api-name "${api_name}" \
    -f support-files/apigw/definition.yaml
    
    # 同步网关环境信息
    python manage.py sync_apigw_stage \
    --api-name "${api_name}" \
    -f support-files/apigw/definition.yaml
    
    # 同步网关策略
    python manage.py sync_apigw_strategies \
    --api-name "${api_name}" \
    -f support-files/apigw/definition.yaml
    
    # 为应用主动授权
    python manage.py grant_apigw_permissions \
    --api-name "${api_name}" \
    -f support-files/apigw/definition.yaml
    
    # 同步网关资源
    python manage.py sync_apigw_resources \
    --api-name "${api_name}" \
    -f support-files/apigw/resources.yaml
    
    # 同步资源文档
    python manage.py sync_resource_docs_by_archive \
    --api-name "${api_name}" \
    -f support-files/apigw/definition.yaml  

    # 创建资源版本并发布
    python manage.py create_version_and_release_apigw \
    --api-name "${api_name}" \
    -f support-files/apigw/definition.yaml --generate-sdks
    
    # 获取网关公钥
    python manage.py fetch_apigw_public_key \
    --api-name "${api_name}"
}

ensure-apt-buildpack() {
    bkrepo_endpoint="$1"
    bkrepo_project="$2"
    region="$3"
    buildpack_url="$4"
    vendor_url="$5"
    buildpack_name="$6"
    
    # apt
    apt_buildpack_version=v2
    python manage.py manage_buildpack \
    --region "${region}" \
    --name "${buildpack_name}" \
    --display_name_zh_cn "安装系统包" \
    --display_name_en "Install Apt package" \
    --description_zh_cn "安装 Aptfile 文件描述的系统依赖包" \
    --description_en "Install the system dependency packages described in the Aptfile file" \
    --tag "${apt_buildpack_version}" \
    --language Apt \
    --type tar \
    --address "${buildpack_url}/${buildpack_name}-${apt_buildpack_version}.tar" \
    --hidden
}

ensure-python-buildpack() {
    bkrepo_endpoint="$1"
    bkrepo_project="$2"
    region="$3"
    buildpack_url="$4"
    vendor_url="$5"
    buildpack_name="$6"
    
    # 默认使用 bkrepo 源
    pip_index_url="${PAAS_BUILDPACK_PYTHON_PIP_INDEX_URL:-${bkrepo_endpoint}/pypi/${bkrepo_project}/pypi/simple/}"
    pip_index_host="$(echo "${bkrepo_endpoint}" | awk -F/ '{print $3}') ${PAAS_PIP_INDEX_HOST:-}"
    python_buildpack_version=v154
    
    python manage.py manage_buildpack \
    --region "${region}" \
    --name "${buildpack_name}" \
    --display_name_zh_cn "Python" \
    --display_name_en "Python" \
    --description_zh_cn "默认 Python 版本为3.6.8" \
    --description_en "The default Python version is 3.6.8" \
    --tag "${python_buildpack_version}" \
    --language Python \
    --type tar \
    --address "${buildpack_url}/${buildpack_name}-${python_buildpack_version}.tar" \
    --environment \
    "BUILDPACK_VENDOR_URL=${vendor_url}/python" \
    "PIP_INDEX_URL=${pip_index_url}" \
    "PIP_EXTRA_INDEX_URL=${bkrepo_endpoint}/pypi/${bkrepo_project}/pypi/simple/" \
    "PIP_INDEX_HOST=${pip_index_host}"
}

ensure-nodejs-buildpack() {
    bkrepo_endpoint="$1"
    bkrepo_project="$2"
    region="$3"
    buildpack_url="$4"
    vendor_url="$5"
    buildpack_name="$6"
    
    # 默认使用 bkrepo 源
    npm_registry="${PAAS_BUILDPACK_NODEJS_BLUEKING_NPM_REGISTRY:-${bkrepo_endpoint}/npm/${bkrepo_project}/npm/}"
    nodejs_buildpack_version=v163
    
    python manage.py manage_buildpack \
    --region "${region}" \
    --name "${buildpack_name}" \
    --display_name_zh_cn "NodeJS" \
    --display_name_en "NodeJS" \
    --description_zh_cn "默认 Node 版本为10.10.0; 支持 npm run build 及缓存加速功能" \
    --description_en "Default Node version is 10.10.0; supports npm run build and cache acceleration" \
    --tag "${nodejs_buildpack_version}" \
    --language NodeJS \
    --type tar \
    --address "${buildpack_url}/${buildpack_name}-${nodejs_buildpack_version}.tar" \
    --environment \
    "STDLIB_FILE_URL=${vendor_url}/common/v7/stdlib.sh" \
    "S3_DOMAIN=${vendor_url}/nodejs" \
    "NPM_REGISTRY=${npm_registry}"
}

ensure-golang-buildpack() {
    bkrepo_endpoint="$1"
    bkrepo_project="$2"
    region="$3"
    buildpack_url="$4"
    vendor_url="$5"
    buildpack_name="$6"
    
    # golang
    go_buildpack_version=v153
    python manage.py manage_buildpack \
    --region "${region}" \
    --name "${buildpack_name}" \
    --display_name_zh_cn "Golang" \
    --display_name_en "Golang" \
    --description_zh_cn "默认 Go 版本为1.12，支持 GoModules/Vendor 环境" \
    --description_en "Default Go version is 1.12 and supports GoModules/Vendor environment" \
    --tag "${go_buildpack_version}" \
    --language Go \
    --type tar \
    --address "${buildpack_url}/${buildpack_name}-${go_buildpack_version}.tar" \
    --environment \
    "GO_BUCKET_URL=${vendor_url}/golang" \
    "GOPROXY=${PAAS_BUILDPACK_GOLANG_GOPROXY}"
}

ensure-buleking-image() {
    region="$1"
    apt_buildpack_name="$2"
    python_buildpack_name="$3"
    nodejs_buildpack_name="$4"
    golang_buildpack_name="$5"
    
    image_name="blueking"
    python manage.py manage_image \
    --region "${region}" \
    --image "${PAAS_APP_IMAGE}" \
    --name "${image_name}" \
    --display_name_zh_cn "蓝鲸基础镜像" \
    --display_name_en "Blueking Basic Image" \
    --description_zh_cn "基于 Ubuntu，支持多构建工具组合构建" \
    --description_en "Ubuntu-based, multi-buildpack combination build support" \
    --label secureEncrypted=1
    python manage.py bind_buildpacks --image "${image_name}" --buildpack-name "${apt_buildpack_name}"
    python manage.py bind_buildpacks --image "${image_name}" --buildpack-name "${python_buildpack_name}"
    python manage.py bind_buildpacks --image "${image_name}" --buildpack-name "${nodejs_buildpack_name}"
    python manage.py bind_buildpacks --image "${image_name}" --buildpack-name "${golang_buildpack_name}"
}

ensure-legacy-image() {
    region="$1"
    apt_buildpack_name="$2"
    python_buildpack_name="$3"
    nodejs_buildpack_name="$4"
    golang_buildpack_name="$5"
    
    legacy_image_name="legacy-blueking"
    python manage.py manage_image \
    --region "${region}" \
    --image "${PAAS_APP_IMAGE}" \
    --name "${legacy_image_name}" \
    --display_name_zh_cn "蓝鲸基础镜像（旧）" \
    --display_name_en "Blueking Basic Image（legacy）" \
    --description_zh_cn "基于 Ubuntu，支持多构建工具组合构建" \
    --description_en "Ubuntu-based, multi-buildpack combination build support" \
    --label secureEncrypted=1 category=legacy_app
    python manage.py bind_buildpacks --image "${legacy_image_name}" --buildpack-name "${apt_buildpack_name}"
    python manage.py bind_buildpacks --image "${legacy_image_name}" --buildpack-name "${python_buildpack_name}"
    python manage.py bind_buildpacks --image "${legacy_image_name}" --buildpack-name "${nodejs_buildpack_name}"
    python manage.py bind_buildpacks --image "${legacy_image_name}" --buildpack-name "${golang_buildpack_name}"
}

ensure-smart-image() {
    python manage.py push_smart_image --image "${PAAS_APP_IMAGE}"
}

ensure-runtimes() {
    region=default
    stack="${PAAS_STACK:-heroku-18}"
    bkrepo_endpoint="${PAAS_BLOBSTORE_BKREPO_ENDPOINT%/}"
    bkrepo_project="${PAAS_BLOBSTORE_BKREPO_PROJECT:-bkpaas}"
    runtimes_url="${PAAS_RUNTIMES_URL:-${bkrepo_endpoint}/generic/${bkrepo_project}/bkpaas3-platform-assets}"
    # 此处需和 paas-stack chart 中 extraInitial.devops 参数中路径一致，否则会导致部署失败
    buildpack_url="${runtimes_url}/runtimes/${stack}/buildpacks"
    vendor_url="${runtimes_url}/runtimes/${stack}/vendor"
    
    # apt
    apt_buildpack_name=bk-buildpack-apt
    ensure-apt-buildpack "${bkrepo_endpoint}" "${bkrepo_project}" "${region}" "${buildpack_url}" "${vendor_url}" "${apt_buildpack_name}"
    
    # python
    python_buildpack_name=bk-buildpack-python
    ensure-python-buildpack "${bkrepo_endpoint}" "${bkrepo_project}" "${region}" "${buildpack_url}" "${vendor_url}" "${python_buildpack_name}"
    
    # nodejs
    nodejs_buildpack_name=bk-buildpack-nodejs
    ensure-nodejs-buildpack "${bkrepo_endpoint}" "${bkrepo_project}" "${region}" "${buildpack_url}" "${vendor_url}" "${nodejs_buildpack_name}"
    
    # golang
    golang_buildpack_name=bk-buildpack-go
    ensure-golang-buildpack "${bkrepo_endpoint}" "${bkrepo_project}" "${region}" "${buildpack_url}" "${vendor_url}" "${golang_buildpack_name}"
    
    # blueking image
    ensure-buleking-image "${region}" "${apt_buildpack_name}" "${python_buildpack_name}" "${nodejs_buildpack_name}" "${golang_buildpack_name}"
    
    # legacy blueking image
    ensure-legacy-image "${region}" "${apt_buildpack_name}" "${python_buildpack_name}" "${nodejs_buildpack_name}" "${golang_buildpack_name}"
}

ensure-init-data() {
    python manage.py better_loaddata fixtures/* -e engine.deploystepmeta -e engine.stepmetaset -e templates.template
    # 之前是在 paasng/fixtures/accounts.yaml 通过 fixture 添加可调用系统 API 的应用，后续添加直接通过命令更方便
    python manage.py create_authed_app_user --bk_app_code=bk_dataweb  --role=50
    python manage.py create_authed_app_user --bk_app_code=bk_bkdata  --role=50
    python manage.py create_3rd_party_apps --source extra_fixtures/3rd_apps.yaml --app_codes "${PAAS_THIRD_APP_INIT_CODES}" --override=true
}

ensure-runtime-steps() {
    python manage.py loaddata fixtures/step_meta.yaml
}

ensure-templates() {
  python manage.py loaddata fixtures/template.yaml
}

ensure-runtimes-fixtures() {
    ensure-runtimes
    ensure-runtime-steps
    ensure-templates
}

ensure-service(){
    python manage.py update_remote_services_config
}

migrate-perm(){
    python manage.py migrate_bkpaas3_perm
}

call_steps ensure-apigw ensure-runtimes-fixtures ensure-init-data ensure-service ensure-smart-image migrate-perm
