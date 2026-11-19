### Function Description
List the base images available to a module for the buildpack build method, together with the buildpacks each base image offers.

When updating the build config, use `image` as `bp_stack_name` and pick `buildpacks` only from the same entry. The same language has different ids under different base images.

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
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/bp_runtimes/
```

### Response Example
```json
[
    {
        "image": "cnb-heroku-builder-noble",
        "slugbuilder": {"id": 24, "name": "cnb-heroku-builder-noble", "display_name": "Ubuntu24", "description": "", "image": "mirrors.example.com/bkpaas/builder-heroku-noble", "tag": "v2.5.0"},
        "slugrunner": {"id": 24, "name": "cnb-heroku-builder-noble", "display_name": "Ubuntu24", "description": "", "image": "mirrors.example.com/bkpaas/run-heroku-noble", "tag": "v2.5.0"},
        "buildpacks": [
            {"id": 48, "language": "Aptfile", "name": "bk-buildpack-apt", "display_name": "apt", "description": ""},
            {"id": 54, "language": "Python", "name": "bk-buildpack-python", "display_name": "blueking/python", "description": ""}
        ]
    }
]
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| image | string | Base image name, i.e. `bp_stack_name` of the build config |
| slugbuilder | object | Builder image; `display_name` is shown in the console |
| slugrunner | object | Runner image |
| buildpacks | list | Buildpacks available on this base image |
| buildpacks[].id | int | Buildpack ID for `buildpacks[].id` of the build config |
| buildpacks[].language | string | Language of the buildpack |
