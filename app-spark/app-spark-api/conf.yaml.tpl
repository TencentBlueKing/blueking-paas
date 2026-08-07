## app-spark-api 配置模板

## Django 基础配置
# SECRET_KEY: ''
# DEBUG: false
# ALLOWED_HOSTS: ['*']

## 国际化
# LANGUAGE_CODE: zh-hans
# LANGUAGES:
#   - [zh-hans, 简体中文]
#   - [en, English]
# TIME_ZONE: Asia/Shanghai
# LANGUAGE_COOKIE_NAME: blueking_language
# LANGUAGE_COOKIE_PATH: /
# LANGUAGE_COOKIE_DOMAIN: ''

## 数据库（引擎固定为 MySQL，必填）
## 未配置 DATABASE_NAME 时服务启动会报错
# DATABASE_NAME: app_spark
# DATABASE_USER: ''
# DATABASE_PASSWORD: ''
# DATABASE_HOST: ''
# DATABASE_PORT: ''
# DATABASE_OPTIONS: {}

## 缓存
## 优先级最高，若不配置则默认使用本地临时文件缓存（仅适用于本地开发）
## 生产环境请配置远程服务缓存（如 RedisCache、DatabaseCache），以保证多副本多 worker 时缓存数据一致
# DEFAULT_CACHE_CONFIG:

## 是否启用多租户模式，仅支持在初次部署时配置，部署后不支持动态调整
# ENABLE_MULTI_TENANT_MODE: false

## ---------------------------------- 各系统地址相关配置 ----------------------------------

## 统一登录页面地址，用于模板渲染，必填
# LOGIN_FULL: ''

## -------------------------------- 用户鉴权模块 bkpaas_auth SDK 相关配置 --------------------------------

## 是否启用多租户模式，需和 ENABLE_MULTI_TENANT_MODE 保持一致
# BKAUTH_ENABLE_MULTI_TENANT_MODE: false

## 用户身份校验类型，默认值为 bk_token
# BKAUTH_BACKEND_TYPE: bk_token
## 用于获取 Token 的 App Code
# BKAUTH_TOKEN_APP_CODE: ''
## 用于获取 Token 的 App Secret
# BKAUTH_TOKEN_SECRET_KEY: ''
## bk-login 网关环境，默认值为 prod
# BKAUTH_BK_LOGIN_APIGW_STAGE: prod
## 如果当前环境没有 bk-login 网关，则设置 BKAUTH_USER_INFO_APIGW_URL 为空字符串，bkpaas_auth 将使用 BKAUTH_USER_COOKIE_VERIFY_URL
## 如果设置了有效的 BKAUTH_USER_INFO_APIGW_URL，BKAUTH_USER_COOKIE_VERIFY_URL 配置将被忽略，使用网关进行用户身份校验
## 多租户模式下（BKAUTH_ENABLE_MULTI_TENANT_MODE=true）必须设置有效的 BKAUTH_USER_INFO_APIGW_URL
# BKAUTH_USER_INFO_APIGW_URL: ''
## 验证用户登录态（是否过期）的地址
# BKAUTH_USER_COOKIE_VERIFY_URL: ''
## 通过 Token 获取用户信息 API
# BKAUTH_TOKEN_USER_INFO_ENDPOINT: ''

## 静态资源
# STATIC_URL: /static/
