### 功能描述
根据下载链接上传源码包至平台

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | --- | -------- |
| app_code | string | 是 | 应用 ID  |
| modules  | string | 是 | 模块名称 |

#### 2、接口参数：

| 字段            | 类型    | 是否必填 | 描述                   |
| --------------- | ------- | -------- | ---------------------- |
| package_url     | string  | 是       | 源码包下载路径         |
| version         | string  | 否       | 源码包版本号           |
| allow_overwrite | boolean | 否       | 是否允许覆盖原有的源码包 |

### 请求示例
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' -d '{ "package_url": "https://example.com/generic/example.tar.gz", "version": "0.0.5" }' --insecure http://bkapi.example.com/api/bkpaas3/stag/bkapps/applications/app_code/modules/default/source_package/link/
```

### 返回结果示例
#### 正常返回
```json
{
    "id": 1347,
    "version": "0.0.5",
    "package_name": "package_name:0.0.5",
    "package_size": "1415656",
    "sha256_signature": "a0c5e14c38eeaf3681bd5b429338e4e95ea8af3f30c05348a1479cfcf1cdf4d1",
    "is_deleted": false,
    "updated": "2024-08-20 19:37:00",
    "created": "2024-08-20 19:37:00",
    "operator": "operator name"
}
```
#### 异常返回
```
{
    "code": "UNSUPPORTED_SOURCE_ORIGIN",
    "detail": "未支持的源码来源"
}
```


### 返回结果参数说明

| 字段             | 类型   | 描述       |
| ---------------- | ------ | ---------- |
| version          | string | 版本信息   |
| package_name     | string | 源码包名称 |
| package_size     | string | 源码包大小 |
| sha256_signature | string | sha256数字签名 |
| updated          | string | 更新时间   |
| created          | string | 创建时间   |
| is_deleted       | boolean | 是否软删除 |
| operator         | string | 操作人 |