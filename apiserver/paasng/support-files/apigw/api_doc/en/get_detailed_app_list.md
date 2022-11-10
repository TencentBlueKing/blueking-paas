### Resource Description
Get App details

### Get your access_token
Before calling the interface, please obtain your access_token. For specific instructions, please refer to [using access_token to access PaaS V3](https://bk.tencent.com/docs/markdown/PaaS3.0/topics/paas/access_token)

### Call example
```bash
curl -X GET -H 'Accept: */*' -H 'X-BKAPI-AUTHORIZATION: {"access_token": "Your access_token"}' http://bkapi.example.com/api/bkpaas3/bkapps/applications/lists/detailed
```

### Request parameter Description

| limit                | number number <br/>of results                                |
| -------------------- | ------------------------------------------------------------ |
| offset               | number <br/>page turn skip number                            |
| Exclude_collaborated | boolean<br/>Default: false <br/><br/>whether to exclude apps with collaborator permissions, which is not excluded by default. If true, it means that only the |
| Include_apps         | boolean<br/>Default: false <br/><br/>whether to include off-shelf apps, default not |
| language             | string <br/><br/>APP programming language                    |
| Search_term          | string <br/><br/>search keyword                              |
| Source_source        | int <br/><br/>source code source, currently supports 1 (code warehouse), 2 (blue whale LessCode) |
| type                 | str <br/>is <br/><br/>filtered by app type. Currently, it supports: default, engineless_app, bk_plugin |
| Order_by             | string <br/><br/>sorting, optional values: code, created, last_deployed_date, latest_operated_at, default is ascending, and descending is followed by "increment," such as "increment created |

### Return result
```json
{
    "count": 2,
    "next": "http://bkpaas.example.com/backend/api/bkapps/applications/lists/detailed?limit=12&amp;offset=12",
    "previous": null,
    "results": [
        {
            "application": {
                "id": "130bd72a-dbf5-419c-8357-9ed914341234",
                "region_name": "Internal version",
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
                "name": "I am v3t",
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
                "region_name": "Hybrid Cloud Version",
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
                "name": "Test 8",
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

### Return result description

| count    | number<br/>Total                            |
| -------- | ------------------------------------------- |
| next     | string<br/>next page address                |
| previous | string<br/>previous page address            |
| results  | dict, see the table below for field details |

#### result Field Detail

| application | dict, see the table below for field details                  |
| ----------- | ------------------------------------------------------------ |
| product     | dict, see the table below for field details                  |
| marked      | boolean<br/>descripton: Whether to focus on<br/>example: true |

- ##### application Field Detail

  | description:         | BlueKing App                                                 |
  | -------------------- | ------------------------------------------------------------ |
  | id                   | string<br/>example: 87ce9623-39e9-4d10-bfc4-c6827d781fc7<br/>APP UUID |
  | region               | string<br/>example: ieod<br/>App area                        |
  | region_name          | string<br/>example: Tencent internal version<br/>Chinese name of the region |
  | source_type          | string<br/>App Source Code Hosting Types                     |
  | source_repo_id       | string<br/>App Source Code Hosting id                        |
  | is_active            | boolean<br/>Is the app active                                |
  | last_deployed_date   | boolean<br/>App Recent Deployment Time                       |
  | code                 | string<br/>App Code                                          |
  | name                 | string<br/>descrition: App Name                              |
  | logo_url             | string<br/>descrition: App Logo Address<br/>example: http://example.com/app-logo/blueking_app_default.png |
  | language             | string<br/>Programming languages used by the app             |
  | source_init_template | string<br/>Name of the template used during app initialization |
  | created              | string($dateTime)<br/>App Creation Time                      |
  | updated              | string($dateTime)<br/>App modification time                  |
  | deploy_info          | dict, see the table below for field details                  |

  ##### deploy_info Field Detail

  - stag

    | deployed | bool<br/>example: true<br/>Whether to deploy                 |
    | -------- | ------------------------------------------------------------ |
    | url      | string<br/>example:<br/> http://apps.example.com/stag--appid/<br/>Access Links |

  - prod

    | deployed | bool<br/>example: false<br/>Whether to deploy                |
    | -------- | ------------------------------------------------------------ |
    | url      | string<br/>example: <br/>http://apps.example.com/appid/<br/> |

- ##### product Field Detail

  | description: | App Market App                                               |
  | ------------ | ------------------------------------------------------------ |
  | name         | string<br/>example: Awesome App<br/>APP UUID                 |
  | logo         | string<br/>example: http://example.com/app-logo/awesome-app.png<br/>App Logo Address |