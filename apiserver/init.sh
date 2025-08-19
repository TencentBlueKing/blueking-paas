#!/bin/bash
##
## TencentBlueKing is pleased to support the open source community by making
## 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
## Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
## Licensed under the MIT License (the "License"); you may not use this file except
## in compliance with the License. You may obtain a copy of the License at
##
##     http://opensource.org/licenses/MIT
##
## Unless required by applicable law or agreed to in writing, software distributed under
## the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
## either express or implied. See the License for the specific language governing permissions and
## limitations under the License.
##
## We undertake not to change the open source license (MIT license) applicable
## to the current version of the project delivered to anyone in the future.
##

set -eo pipefail

call_steps() {
    steps="$*"
    commands=("$@")
    pids=()

    for index in ${!commands[*]}; do
        command=${commands[$index]}
        echo "Starting job $(($index+1)) with command: ${command}"
        ${command} &
        pids+=("$!")
    done

    code=0
    for index in ${!pids[*]}; do
        job=${pids[$index]}
        command=${commands[$index]}
        if wait ${job}; then
            echo "Job $(($index+1)) with command: ${command} successfully completed"
        else
            code=1
            echo "Process $(($index+1)) with command: ${command} failed"
        fi
    done

    return ${code}
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
    
    # 为应用主动授权
    python manage.py grant_apigw_permissions \
    --api-name "${api_name}" \
    -f support-files/apigw/definition.yaml
    
    # 同步网关资源
    python manage.py sync_apigw_resources \
    --delete \
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
    buildpack_url="$3"
    vendor_url="$4"
    buildpack_name="$5"
    
    # apt
    apt_buildpack_version=v2
    python manage.py manage_buildpack \
    --name "${buildpack_name}" \
    --display_name_zh_cn "安装系统包" \
    --display_name_en "Install Apt package" \
    --description_zh_cn "安装 Aptfile 文件描述的系统依赖包" \
    --description_en "Install the system dependency packages described in the Aptfile file" \
    --tag "${apt_buildpack_version}" \
    --language Apt \
    --type tar \
    --address "${buildpack_url}/${buildpack_name}-${apt_buildpack_version}.tar"
}

ensure-python-buildpack() {
    bkrepo_endpoint="$1"
    bkrepo_project="$2"
    buildpack_url="$3"
    vendor_url="$4"
    buildpack_name="$5"
    
    # 默认使用 bkrepo 源
    pip_index_url="${PAAS_BUILDPACK_PYTHON_PIP_INDEX_URL:-${bkrepo_endpoint}/pypi/${bkrepo_project}/pypi/simple/}"
    pip_index_host="$(echo "${bkrepo_endpoint}" | awk -F/ '{print $3}') ${PAAS_PIP_INDEX_HOST:-}"
    python_buildpack_version=v213
    
    python manage.py manage_buildpack \
    --name "${buildpack_name}" \
    --display_name_zh_cn "Python" \
    --display_name_en "Python" \
    --description_zh_cn "默认 Python 版本为3.10.5" \
    --description_en "The default Python version is 3.10.5" \
    --tag "${python_buildpack_version}" \
    --language Python \
    --type tar \
    --address "${buildpack_url}/${buildpack_name}-${python_buildpack_version}.tar" \
    --environment \
    "BUILDPACK_S3_BASE_URL=${vendor_url}/runtimes/python" \
    "BUILDPACK_VENDOR_URL=${vendor_url}/runtimes/python" \
    "PIP_INDEX_URL=${pip_index_url}" \
    "PIP_EXTRA_INDEX_URL=${bkrepo_endpoint}/pypi/${bkrepo_project}/pypi/simple/" \
    "PIP_INDEX_HOST=${pip_index_host}"
}

ensure-nodejs-buildpack() {
    bkrepo_endpoint="$1"
    bkrepo_project="$2"
    buildpack_url="$3"
    vendor_url="$4"
    buildpack_name="$5"
    
    # 默认使用 bkrepo 源
    npm_registry="${PAAS_BUILDPACK_NODEJS_BLUEKING_NPM_REGISTRY:-${bkrepo_endpoint}/npm/${bkrepo_project}/npm/}"
    nodejs_buildpack_version=v163
    
    python manage.py manage_buildpack \
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
    "STDLIB_FILE_URL=${vendor_url}/common/buildpack-stdlib/v7/stdlib.sh" \
    "S3_DOMAIN=${vendor_url}/runtimes/nodejs/node/release/linux-x64" \
    "NPM_REGISTRY=${npm_registry}"
}

ensure-golang-buildpack() {
    bkrepo_endpoint="$1"
    bkrepo_project="$2"
    buildpack_url="$3"
    vendor_url="$4"
    buildpack_name="$5"
    
    # golang
    go_buildpack_version=v191
    python manage.py manage_buildpack \
    --name "${buildpack_name}" \
    --display_name_zh_cn "Golang" \
    --display_name_en "Golang" \
    --description_zh_cn "默认 Go 版本为1.20.14，最大支持版本1.22.3" \
    --description_en "Default Go Version: 1.20.14, Highest supported version: 1.22.3" \
    --tag "${go_buildpack_version}" \
    --language Go \
    --type tar \
    --address "${buildpack_url}/${buildpack_name}-${go_buildpack_version}.tar" \
    --environment \
    "GO_BUCKET_URL=${vendor_url}/runtimes/golang" \
    "GOPROXY=${PAAS_BUILDPACK_GOLANG_GOPROXY}"
}

ensure-blueking-image() {
    apt_buildpack_name="$1"
    python_buildpack_name="$2"
    nodejs_buildpack_name="$3"
    golang_buildpack_name="$4"
    
    image_name="blueking"
    python manage.py manage_image \
    --type "legacy" \
    --image "${PAAS_APP_IMAGE}" \
    --name "${image_name}" \
    --display_name_zh_cn "蓝鲸基础镜像" \
    --display_name_en "Blueking Basic Image" \
    --description_zh_cn "基于 Ubuntu，支持多构建工具组合构建" \
    --description_en "Ubuntu-based, multi-buildpack combination build support" \
    --label secureEncrypted=1 supportHttp=1 normal_app=1 smart_app=1
    python manage.py bind_buildpacks --image "${image_name}" --buildpack-name "${apt_buildpack_name}"
    python manage.py bind_buildpacks --image "${image_name}" --buildpack-name "${python_buildpack_name}"
    python manage.py bind_buildpacks --image "${image_name}" --buildpack-name "${nodejs_buildpack_name}"
    python manage.py bind_buildpacks --image "${image_name}" --buildpack-name "${golang_buildpack_name}"

    cnb_image_name="blueking-cloudnative"
    python manage.py manage_image \
    --type "cnb" \
    --slugbuilder "${PAAS_HEROKU_BUILDER_IMAGE}" \
    --slugrunner "${PAAS_HEROKU_RUNNER_IMAGE}" \
    --name "${cnb_image_name}" \
    --display_name_zh_cn "蓝鲸基础镜像" \
    --display_name_en "Blueking Basic Image" \
    --description_zh_cn "基于 Ubuntu，支持多构建工具组合构建" \
    --description_en "Ubuntu-based, multi-buildpack combination build support" \
    --environment "CNB_PLATFORM_API=0.11" "CNB_RUN_IMAGE=${PAAS_HEROKU_RUNNER_IMAGE}" "CNB_SKIP_TLS_VERIFY=${PAAS_APP_DOCKER_REGISTRY_SKIP_TLS_VERIFY:-false}" \
    --label secureEncrypted=1 supportHttp=1 isCloudNativeBuilder=1 cnative_app=1
    python manage.py bind_buildpacks --image "${cnb_image_name}" --buildpack-name "${apt_buildpack_name}"
    python manage.py bind_buildpacks --image "${cnb_image_name}" --buildpack-name "${python_buildpack_name}"
    python manage.py bind_buildpacks --image "${cnb_image_name}" --buildpack-name "${nodejs_buildpack_name}"
    python manage.py bind_buildpacks --image "${cnb_image_name}" --buildpack-name "${golang_buildpack_name}"
}

ensure-legacy-image() {
    apt_buildpack_name="$1"
    python_buildpack_name="$2"
    nodejs_buildpack_name="$3"
    golang_buildpack_name="$4"
    
    legacy_image_name="legacy-blueking"
    python manage.py manage_image \
    --type "legacy" \
    --image "${PAAS_APP_IMAGE}" \
    --name "${legacy_image_name}" \
    --display_name_zh_cn "蓝鲸基础镜像（旧）" \
    --display_name_en "Blueking Basic Image（legacy）" \
    --description_zh_cn "基于 Ubuntu，支持多构建工具组合构建" \
    --description_en "Ubuntu-based, multi-buildpack combination build support" \
    --label secureEncrypted=1 category=legacy_app legacy_app=1
    python manage.py bind_buildpacks --image "${legacy_image_name}" --buildpack-name "${apt_buildpack_name}"
    python manage.py bind_buildpacks --image "${legacy_image_name}" --buildpack-name "${python_buildpack_name}"
    python manage.py bind_buildpacks --image "${legacy_image_name}" --buildpack-name "${nodejs_buildpack_name}"
    python manage.py bind_buildpacks --image "${legacy_image_name}" --buildpack-name "${golang_buildpack_name}"
}

ensure-smart-image() {
    python manage.py push_smart_image --image "${PAAS_APP_IMAGE}" --type legacy --dry-run "${PAAS_SKIP_PUSH_SMART_BASE_IMAGE:-False}"
    python manage.py push_smart_image --image "${PAAS_HEROKU_RUNNER_IMAGE}" --type cnb --dry-run "${PAAS_SKIP_PUSH_SMART_BASE_IMAGE:-False}"
}

ensure-runtimes() {
    stack="${PAAS_STACK:-heroku-18}"
    bkrepo_endpoint="${PAAS_BLOBSTORE_BKREPO_ENDPOINT%/}"
    bkrepo_project="${PAAS_BLOBSTORE_BKREPO_PROJECT:-bkpaas}"
    runtimes_url="${PAAS_RUNTIMES_URL:-${bkrepo_endpoint}/generic/${bkrepo_project}/bkpaas3-platform-assets}"
    # 此处需和 paas-stack chart 中 extraInitial.devops 参数中路径一致，否则会导致部署失败
    buildpack_url="${runtimes_url}/buildpacks"
    vendor_url="${runtimes_url}"
    
    # apt
    apt_buildpack_name=bk-buildpack-apt
    ensure-apt-buildpack "${bkrepo_endpoint}" "${bkrepo_project}" "${buildpack_url}" "${vendor_url}" "${apt_buildpack_name}"
    
    # python
    python_buildpack_name=bk-buildpack-python
    ensure-python-buildpack "${bkrepo_endpoint}" "${bkrepo_project}" "${buildpack_url}" "${vendor_url}" "${python_buildpack_name}"
    
    # nodejs
    nodejs_buildpack_name=bk-buildpack-nodejs
    ensure-nodejs-buildpack "${bkrepo_endpoint}" "${bkrepo_project}" "${buildpack_url}" "${vendor_url}" "${nodejs_buildpack_name}"
    
    # golang
    golang_buildpack_name=bk-buildpack-go
    ensure-golang-buildpack "${bkrepo_endpoint}" "${bkrepo_project}" "${buildpack_url}" "${vendor_url}" "${golang_buildpack_name}"
    
    # blueking image
    ensure-blueking-image "${apt_buildpack_name}" "${python_buildpack_name}" "${nodejs_buildpack_name}" "${golang_buildpack_name}"
    
    # legacy blueking image
    ensure-legacy-image "${apt_buildpack_name}" "${python_buildpack_name}" "${nodejs_buildpack_name}" "${golang_buildpack_name}"
}

ensure-init-data() {
    python manage.py loaddata fixtures/smart_advisor.yaml
    # 之前是在 paasng/fixtures/accounts.yaml 通过 fixture 添加可调用系统 API 的应用，后续添加直接通过命令更方便
    python manage.py create_authed_app_user --bk_app_code=bk_dataweb  --role=50
    python manage.py create_authed_app_user --bk_app_code=bk_bkdata  --role=50
    python manage.py create_authed_app_user --bk_app_code=bk_apigateway --role=50
    python manage.py create_authed_app_user --bk_app_code=bk_log_search --role=50
    python manage.py create_authed_app_user --bk_app_code=bk_monitorv3 --role=50
    python manage.py create_authed_app_user --bk_app_code=bk_paas3 --role=60
    python manage.py create_authed_app_user --bk_app_code=bk_sops --role=70
    python manage.py create_authed_app_user --bk_app_code=bk_lesscode --role=80
    python manage.py create_3rd_party_apps --source extra_fixtures/3rd_apps.yaml --app_codes "${PAAS_THIRD_APP_INIT_CODES}" --override=true
    # 将开发者中心注册到通知中心
    python manage.py register_to_bk_notice
    # 初始化本地 redis 增强服务
    python manage.py loaddata fixtures/services.yaml
    # 初始化本地 redis 增强服务的 Plan
    python manage.py init_redis_service_plans
}

ensure-runtime-steps() {
    python manage.py sync_step_meta_set
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
    # admin 用户拥有全量权限，不应占用配额且不需要授权
    python manage.py migrate_bkpaas3_perm --exclude-users admin
}

call_steps ensure-apigw ensure-runtimes-fixtures ensure-init-data ensure-service ensure-smart-image migrate-perm
