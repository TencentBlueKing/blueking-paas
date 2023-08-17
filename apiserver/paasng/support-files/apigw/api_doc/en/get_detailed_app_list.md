### Feature Description
Get App details

### Request Parameters

#### 1. Interface Parameters:

| Field | Type | Required | Description |
| ------ | ------ | ------ | ------ |
| limit | number | No | Result quantity |
| offset | number | No | Pagination skip quantity |
| exclude_collaborated | boolean | No | Whether to exclude apps with collaborator permissions, default is not excluded. If true, it means to return only the apps I created |
| include_inactive | boolean | No | Whether to include inactive apps, default is not included |
| language | string | No | APP programming language |
| search_term | string | No | Search keyword |
| source_origin | int | No | Source code origin, currently supports 1 (code repository) and 2 (BlueKing LessCode) |
| type | str | No | Filter by app type, currently supports: default (default), engineless_app (engineless app), bk_plugin (BlueKing plugin) |
| order_by | string | No | Sort, optional values: code, created, last_deployed_date, latest_operated_at, default is ascending, add - for descending, such as -created |

### Request Example
```bash
curl -X GET -H 'Accept: */*' -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/bkapps/applications/lists/detailed
```

#### Get your access_token
Before calling the interface, please get your access_token first. For specific guidance, please refer to [Using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Response Result Example
```json
{
    "count": 2,
    "next": "http://bkpaas.example.com/backend/api/bkapps/applications/lists/detailed?limit=12&amp;offset=12",
    "previous": null,
    "results": [
        {
            "application": {
                "id": "130bd72a-dbf5-419c-8357-9ed914341234",
                "region_name": "内部版",
                "logo_url": "http://example.com/app-logo/blueking_app_default.png",
                "deploy_status": true,
                "deploy_info": {
                    "stag": {
                        "url": "http://apps.example.com/ieod-bkapp-aaaa-stag/",
                        "deployed": true
                    },
                    "prod": {
                        "url": "http://apps.example.com/ieod-bkapp-aaaa-prod/",
                        "deployed": true
                    }
                },
                "region": "ieod",
                "created": "2018-04-25 12:08:54",
                "updated": "2018-06-19 16:54:37",
                "owner": "0236c4ff908f528b",
                "code": "verylongnameaaaa",
                "name": "我就是v3t",
                "language": "Go",
                "source_init_template": "go_gin_hello_world",
                "source_type": "bk_svn",
                "source_repo_id": 432,
                "app_type": "backend",
                "is_active": true,
                "last_deployed_date": null,
                "creator": "0236c4ff908f528b",
                "is_deleted": false
            },
            "product": null,
            "marked": true
        },
        {
            "application": {
                "id": "d403880b-6c46-4edf-b1a0-24363b61234",
                "region_name": "混合云版",
                "logo_url": "http://example.com/app-logo/blueking_app_default.png",
                "deploy_status": true,
                "deploy_info": {
                    "stag": {
                        "url": "http://apps.example.com/clouds-bkapp-appid-stag/",
                        "deployed": true
                    },
                    "prod": {
                        "url": null,
                        "deployed": false
                    }
                },
                "region": "clouds",
                "created": "2018-04-10 16:34:36",
                "updated": "2018-04-10 16:34:36",
                "owner": "0236c4ff908f528b",
                "code": "appid8",
                "name": "测试8",
                "language": "Python",
                "source_init_template": "dj18_hello_world",
                "source_type": "bk_svn",
                "source_repo_id": 425,
                "app_type": "backend",
                "is_active": true,
                "last_deployed_date": null,
                "creator": "0236c4ff908f528b",
                "is_deleted": false
            },
            "product": null,
            "marked": false
        }
	]
}

```

### Response Result Parameter Description

| Field | Type | Description |
| ------ | ------ | ------ |
| count | number | Total count |
| next | string | Next page address |
| previous | string | Previous page address |
| results | array | Result list, including app information |

results internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| application | object | BlueKing app information |
| product | object | App market app information |
| marked | boolean | Whether it is marked |

application internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| id | string | App UUID |
| region | string | App region |
| region_name | string | Chinese name corresponding to the region |
| source_type | string | App source code hosting type |
| source_repo_id | string | App source code hosting id |
| is_active | boolean | Whether the app is active |
| last_deployed_date | boolean | App last deployment time |
| code | string | App Code |
| name | string | App name |
| logo_url | string | App Logo address |
| language | string | App programming language |
| source_init_template | string | Template name used when initializing the app |
| created | string | App creation time |
| updated | string | App modification time |
| deploy_info | object | Deployment information |

deploy_info internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| stag | object | Stage information |
| prod | object | Production information |

stag and prod internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| deployed | bool | Whether it is deployed |
| url | string | Access link |

product internal field description:

| Field | Type | Description |
| ------ | ------ | ------ |
| name | string | App UUID |
| logo | string | App logo address |