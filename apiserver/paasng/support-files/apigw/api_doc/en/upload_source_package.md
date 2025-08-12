### Description
Upload source code package to the platform

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Parameter Description |
| -------------- | -------------- | -------- | --------------------- |
| code           | string         | Yes      | Code                  |
| module_name    | string         | Yes      | Module name           |

#### 2. API Parameters:

| Field           | Type    | Required | Description                          |
| --------------- | ------- | -------- | ------------------------------------ |
| package         | file    | Yes      | Source code package file             |
| allow_overwrite | boolean | No       | Whether to allow overwriting existing source code package |


### Return Result Example
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

### Return Result Parameter Description

| Field           | Type   | Description       |
| --------------- | ------ | ----------------- |
| version         | string | Version information |
| package_name    | string | Source code package name |
| package_size    | string | Source code package size |
| sha256_signature | string | sha256 digital signature |
| updated         | string | Update time       |
| created         | string | Creation time     |