### Function Description
List available API gateways for permission apply. Use `name` to search by gateway name.

Recommended flow: call this API to get the target gateway `name`, then call `list_gateway_permission_resources` to inspect resources and current permission status.

### Request Parameters

#### 1. Path Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| app_code | string | Yes | Application ID, e.g. "appid1" |

#### 2. Query Parameters:
| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| name | string | No | Gateway name, e.g. "paasv3" |
| fuzzy | boolean | No | Fuzzy match by name, default true |

### Request Example
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***", "bk_token": "***"}' --insecure 'https://bkapi.example.com/api/bkpaas3/prod/cloudapi-v2/apps/appid1/inner/gateways/?name=paasv3&fuzzy=true'
```

### Response Example
```json
[
    {
        "id": 1,
        "name": "paasv3",
        "description": "PaaS 3.0 Developer Center API Gateway",
        "maintainers": ["admin"],
        "doc_maintainers": {}
    }
]
```

### Response Fields
| Field | Type | Description |
| ----- | ---- | ----------- |
| id | int | Gateway ID |
| name | string | Gateway name |
| description | string | Gateway description |
| maintainers | array | Gateway maintainers |
| doc_maintainers | object | Document maintainer info |

**Status Code Explanation:**
- **200**: Success
