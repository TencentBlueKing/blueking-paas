### Description
Upload the source code package to the platform according to the download link.


### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| code           | string         | Yes      | Application ID        |
| module_name    | string         | Yes      | Module name           |

#### 2. API Parameters:

| Field           | Type    | Required | Description                 |
| --------------- | ------- | -------- | --------------------------- |
| package_url     | string  | Yes      | Source code package download path |
| version         | string  | No       | Source code package version number |
| allow_overwrite | boolean | No       | Whether to allow overwriting the original source code package |

### Request Example
```bash
curl -X POST 'http://bkapi.example.com/api/bkpaas3/stag/bkapps/applications/sundy820/modules/default/source_package/link/' \
  -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' \
  -H 'Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryohLfLFHX1EPDP7rB' \
  --data-binary $'------WebKitFormBoundaryohLfLFHX1EPDP7rB\r\nContent-Disposition: form-data; name="package_url"\r\n\r\n   your source code package link  \r\n------WebKitFormBoundaryohLfLFHX1EPDP7rB\r\nContent-Disposition: form-data; name="version"\r\n\r\n  your version number  \r\n------WebKitFormBoundaryohLfLFHX1EPDP7rB\r\nContent-Disposition: form-data; name="allow_overwrite"\r\n\r\nfalse\r\n------WebKitFormBoundaryohLfLFHX1EPDP7rB--\r\n'
```

### Request Example
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{code}/modules/{module_name}/envs/{environment}/released_info/
```

#### Get your access_token
Before calling the interface, please obtain your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Response Result Example
```json
{
  "version": "v1",
  "package_name": "tmpcvml_dsm.tar.gz",
  "package_size": "4586",
  "sha256_signature": null,
  "updated": "2020-08-24 17:15:51",
  "created": "2020-08-24 17:15:51"
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