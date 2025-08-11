### Description
Upload the source code package to the platform according to the download link.


### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code       | string         | Yes      | Application ID        |
| module         | string         | Yes      | Module name           |

#### 2. API Parameters:

| Field           | Type    | Required | Description                 |
| --------------- | ------- | -------- | --------------------------- |
| package_url     | string  | Yes      | Source code package download path |
| version         | string  | No       | Source code package version number |
| allow_overwrite | boolean | No       | Whether to allow overwriting the original source code package |

### Request Example
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_ticket": "***"}' -d '{ "package_url": "https://example.com/generic/example.tar.gz", "version": "0.0.5" }' --insecure https://paas.example.apigw.o.woav3..com/stag/bkapps/applications/app_code/modules/default/source_package/link/
```

### Response Result Example
#### Success Response
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

#### Exception Response
```
{
    "code": "UNSUPPORTED_SOURCE_ORIGIN",
    "detail": "未支持的源码来源"
}
```

### Response Result Parameter Description

| Field             | Type   | Description       |
| ----------------- | ------ | ----------------- |
| version           | string | Version information |
| package_name      | string | Source code package name |
| package_size      | string | Source code package size |
| sha256_signature  | string | sha256 digital signature |
| updated           | string | Update time       |
| created           | string | Creation time     |
| is_deleted        | boolean | soft delete indicator |
| operator          | string | operator's name |