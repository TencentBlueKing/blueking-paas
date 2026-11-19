### Function Description
Update the build config of a module. The body replaces the current config: fetch it with `get_module_build_config`, change only the needed fields and submit the whole object. `use_bk_ci_pipeline` resets to false when omitted.

- buildpack: `tag_options`, `bp_stack_name` and `buildpacks` are required. `bp_stack_name` comes from `image` of `list_module_bp_runtimes`; every buildpack id must belong to the chosen base image. The same language has different ids under different base images, so pick buildpacks again by language when switching base images. List order is build order.
- dockerfile: `tag_options` and `docker_build_args` (may be empty) are required; provide `dockerfile_path`.
- custom_image: `image_repository` is required. custom_image cannot be switched to or from other build methods.

Redeploy for the change to take effect.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |
| module | string | Yes | Module name, e.g. "default" |

#### 2. Body Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| build_method | string | Yes | buildpack / dockerfile / custom_image |
| tag_options | object | No | Image tag rules: prefix, with_version, with_build_time, with_commit_id |
| bp_stack_name | string | No | Base image name |
| buildpacks | list | No | Ordered buildpacks, each `{"id": <int>}` |
| dockerfile_path | string | No | Dockerfile path |
| docker_build_args | object | No | Docker build args |
| image_repository | string | No | Image repository |
| image_credential_name | string | No | Image credential name |
| use_bk_ci_pipeline | boolean | No | Build in a BK-CI pipeline, defaults to false |

### Request Example
```bash
curl -X POST -H 'Content-Type: application/json' -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' -d '{"build_method":"buildpack","tag_options":{"prefix":null,"with_version":true,"with_build_time":true,"with_commit_id":false},"bp_stack_name":"cnb-heroku-builder-noble","buildpacks":[{"id":54}],"use_bk_ci_pipeline":false}' --insecure https://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/appid1/modules/default/build_config/
```

### Response Example
Returns 204 with no body on success.

**Status Code Explanation:**
- **204**: Updated
- **400**: Missing fields, unsupported build method switch, or buildpack not found
