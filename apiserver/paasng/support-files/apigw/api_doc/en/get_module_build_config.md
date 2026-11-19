### Function Description
Retrieve the current build config of a module. Fields depend on the build method: buildpack returns the base image and buildpacks, dockerfile returns the Dockerfile path and build args, and custom_image returns the image repository.

Call this API before changing the build config, edit the result, then call `update_module_build_config`.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| module | string | Yes | Module name, e.g. "default" |

#### 2. API Parameters:
None.

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/build_config/
```

### Response Example
```json
{
    "build_method": "buildpack",
    "tag_options": {"prefix": null, "with_version": true, "with_build_time": true, "with_commit_id": false},
    "bp_stack_name": "cnb-heroku-builder-noble",
    "buildpacks": [
        {"id": 54, "language": "Python", "name": "bk-buildpack-python", "display_name": "blueking/python", "description": "BlueKing Python buildpack"}
    ],
    "dockerfile_path": null,
    "docker_build_args": null,
    "env_image_repositories": {"stag": "mirrors.example.com/bkapps/appid1/default", "prod": "mirrors.example.com/bkapps/appid1/default"},
    "image_repository": null,
    "image_credential_name": null,
    "use_bk_ci_pipeline": false
}
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| build_method | string | Build method: buildpack / dockerfile / custom_image |
| tag_options | object | Image tag rules |
| bp_stack_name | string | Base image name for buildpack |
| buildpacks | list | Ordered buildpacks for buildpack |
| dockerfile_path | string | Dockerfile path |
| docker_build_args | object | Docker build args |
| env_image_repositories | object | Repositories of images built from source |
| image_repository | string | Image repository for custom_image |
| image_credential_name | string | Image credential name for custom_image |
| use_bk_ci_pipeline | boolean | Whether builds run in a BK-CI pipeline |
