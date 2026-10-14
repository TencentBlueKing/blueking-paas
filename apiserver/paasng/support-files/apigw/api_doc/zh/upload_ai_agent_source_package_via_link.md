### 功能描述

以应用身份，通过下载链接为 AI Agent 应用上传源码包。调用方须具备 AIDEV 系统角色，且目标应用必须是 AI Agent 应用，否则返回 403。

上传逻辑与用户态接口一致，仅上传人由请求体中的 `operator` 指定，响应中的 `operator` 即为该用户。

### 请求参数

#### 1、路径参数

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID，必须是 AI Agent 应用 |
| module | string | 是 | 模块名称 |

#### 2、接口参数

| 字段 | 类型 | 是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| package_url | string | 是 | 源码包下载路径 |
| version | string | 是 | 源码包版本号，必须显式传入，不支持传空字符串或 null |
| operator | string | 是 | 源码包上传人用户名，记录为源码包的上传人，允许使用虚拟账号 |
| allow_overwrite | boolean | 否 | 是否允许覆盖原有的源码包，默认 false |
| build_method | string | 否 | 构建方式，仅 AI Agent 应用支持。可选值：buildpack、dockerfile，不传则保持模块当前配置 |
| dockerfile_path | string | 否 | Dockerfile 路径，build_method 为 dockerfile 时生效，默认 Dockerfile |
| docker_build_args | object | 否 | Docker 构建参数，build_method 为 dockerfile 时生效，默认 {} |

### 请求示例

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"package_url": "https://example.com/generic/example.tar.gz", "version": "0.0.5", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/source_package/link/
```

### 返回结果示例

```
{
    "id": 1347,
    "version": "0.0.5",
    "package_name": "package_name:0.0.5",
    "package_size": "1415656",
    "sha256_signature": "a0c5e14c38eeaf3681bd5b429338e4e95ea8af3f30c05348a1479cfcf1cdf4d1",
    "is_deleted": false,
    "updated": "2024-08-20 19:37:00",
    "created": "2024-08-20 19:37:00",
    "operator": "admin"
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| id | integer | 源码包 ID |
| version | string | 源码包版本号 |
| package_name | string | 源码包文件名 |
| package_size | string | 源码包大小 |
| sha256_signature | string | 源码包 sha256 数字签名 |
| is_deleted | boolean | 源码包是否已被清理 |
| updated | string | 更新时间 |
| created | string | 创建时间 |
| operator | string | 源码包上传人用户名 |
