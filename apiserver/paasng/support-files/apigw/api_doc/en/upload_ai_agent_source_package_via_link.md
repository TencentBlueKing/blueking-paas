### Function Description

Upload a source code package for an AI Agent application according to the download link, using application credentials. The caller must have the AIDEV system role, and the target application must be an AI Agent application, otherwise 403 is returned.

The upload logic is the same as the user-facing API. Only the uploader is specified by the `operator` field in the request body, and the `operator` in the response is that user.

### Request Parameters

#### 1. Path Parameters

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | --------------------- |
| app_code | string | Yes | Application ID. Must be an AI Agent application |
| module | string | Yes | Module name |

#### 2. Interface Parameters

| Field | Type | Required | Description |
| ------- | ------ | ---------- | ------------- |
| package_url | string | Yes | Source code package download path |
| version | string | Yes | Source code package version number. It must be provided explicitly; an empty string or `null` is not accepted |
| operator | string | Yes | Username of the uploader, recorded as the owner of the source package. Virtual accounts are allowed. |
| allow_overwrite | boolean | No | Whether to allow overwriting the original source code package. Default false. |
| build_method | string | No | Build method. Only supported by AI Agent apps. Values: buildpack, dockerfile. If omitted, the module's current build method is kept. |
| dockerfile_path | string | No | Dockerfile path. Effective when build_method is dockerfile. Defaults to Dockerfile. |
| docker_build_args | object | No | Docker build arguments. Effective when build_method is dockerfile. Defaults to {}. |

### Request Example

```
curl -X POST -H 'content-type: application/json' -H 'x-bkapi-authorization: {"bk_app_code": "bkaidev", "bk_app_secret": "***"}' -d '{"package_url": "https://example.com/generic/example.tar.gz", "version": "0.0.5", "operator": "admin"}' --insecure https://bkapi.example.com/api/bkpaas3/stag/system/bkapps/applications/ai-demo/modules/default/source_package/link/
```

### Response Example

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

### Response Parameter Description

| Field | Type | Description |
| ------- | ------ | ------------- |
| id | integer | Source code package ID |
| version | string | Source code package version number |
| package_name | string | Source code package file name |
| package_size | string | Source code package size |
| sha256_signature | string | Source code package sha256 digital signature |
| is_deleted | boolean | Whether the source code package has been cleaned up |
| updated | string | Update time |
| created | string | Creation time |
| operator | string | Username of the uploader |
