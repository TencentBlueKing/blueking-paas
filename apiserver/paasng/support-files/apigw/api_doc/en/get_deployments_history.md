### Description
Get deployment history

### Request Parameters

#### 1. Path Parameters:
None.

#### 2. API Parameters:
None.

### Request Example

```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}'  http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{your_appcode}/deployments/lists
```

### Response Result Example
```json
{
    "count": 2,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": "e09fbf57-303f-483c-85b5-d41d03ec1234",
            "status": "successful",
            "operator": {
                "username": "kunliangwu",
                "id": "xxxxxxxxxxxx"
            },
            "created": "2018-07-27 14:55:53",
            "environment": "stag",
            "repo": {
                "url": "http://svn.o.tencent.com/apps/ktest1/trunk",
                "comment": "",
                "type": "trunk",
                "name": "trunk",
                "revision": "26933"
            },
            "deployment_id": "e09fbf57-303f-483c-85b5-d41d03ec1234"
        },
        {
            "id": "5d5d964d-825d-4fcb-ae42-ab143e6d1234",
            "status": "successful",
            "operator": {
                "username": "admin",
                "id": "xxxxxxxxxxx"
            },
            "created": "2018-07-10 21:47:31",
            "environment": "stag",
            "repo": {
                "url": "http://svn.o.tencent.com/apps/ktest1/trunk",
                "comment": "",
                "type": "trunk",
                "name": "trunk",
                "revision": "26933"
            },
            "deployment_id": "5d5d964d-825d-4fcb-ae42-ab143e6d1234"
        }
	]
}
```

### Response Result Parameter Description

| Field |   Type | Description |
| ------ | ------ | ------ |
| count | int | Deployment history count |
| next | string/null | Next page link |
| previous | string/null | Previous page link |
| results | array | Deployment history list |

results
| Field |   Type | Description |
| ------ | ------ | ------ |
| id | string | Deployment history ID |
| status | string | Deployment status |
| operator | object | Operator information |
| created | string | Creation time |
| environment | string | Environment |
| repo | object | Repository information |
| deployment_id | string | Deployment ID |

operator
| Field |   Type | Description |
| ------ | ------ | ------ |
| username | string | Username |
| id | string | User ID |

repo
| Field |   Type | Description |
| ------ | ------ | ------ |
| url | string | Repository URL |
| comment | string | Comment |
| type | string | Type |
| name | string | Name |
| revision | string | Revision number |