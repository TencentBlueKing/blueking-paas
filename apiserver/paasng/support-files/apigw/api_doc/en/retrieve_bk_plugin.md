### Resource Description

Query the details of a blue whale plug-in type app for internal system use only

### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Input parameter Description

| Field | Type | Required | Description        |
|---------------|----------|-----|------------------------|
| private_token | string   | no | Token allocated by PaaS platform, which must be provided when the app identity of requester is not authenticated by PaaS platform |
| code          |  string   | no | Location parameter, code of plug-in to be queried|

### Return result

```javascript
{
  "plugin": {
    "id": "70604e3d6491472eb0066ff6f7b75617",
    "region": "ieod",
    "name": "bkplugindemo2",
    "code": "bk-plugin-demo2",
    "logo_url": "https://example.com/app-logo/blueking_app_default.png",
    "has_deployed": true,
    "creator": "username",
    "created": "2021-08-13 10:37:29",
    "updated": "2021-08-13 10:37:29"
  },
  "deployed_statuses": {
    "stag": {
      "deployed": true,
      "addresses": [
        {
          "address": "http://stag-dot-bk-plugin-demo2.example.com",
          "type": 2
        },
        {
          "address": "http://foo.example.com",
          "type": 4
        }
      ]
    },
    "prod": {
      "deployed": false,
      "addresses": []
    }
  },
  "profile": {
    "introduction": "a demo plugin",
    "contact": "user1"
  }
}
```

### Return result description

- The API returns a 404 status code when the plug-in can not be queried through code

| Field     | Type | Description                                       |
|-------------------|----------|-------------------------------------------------------|
| plugin            |  object   | Plug-in basics                                              |
| deployed_statuses | object   | The deployment of the plug-in on each environment. When not deployed, the`addresses` field is`[]`|

`deployed_statuses` Object field Description:

| Field | Type  | Description    |
|-----------|---------------|--------------------|
| deployed  | boolean       | Has it been deployed         |
| addresses |array [object] |All Access addresses in the current environment|
| profile   |  object        | Profile information of plug-in         |


`addresses` Element object field Description:

| Field | Type | Description                                 |
|----------|----------|-------------------------------------------------|
| address  | str      | Access address                                            |
| type     |  integer  |Address type. Note: 2 default address; 4 separate domain names added by the user. |

`profile` Element object field Description:

| Field | Type | Description          |
|--------------|----------|--------------------------|
| introduction | str      | Plug-in introduction information                 |
| contact      |  str      | Plug-in contact for multiple plug-ins; Partition|