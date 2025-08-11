### Description
Get brief information of the App

### Request Parameters

#### 1. Path Parameters:
None

#### 2. API Parameters:
None

### Request Example

```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your_access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/lists/minimal
```

### Response Result Example
```json
{
    "count": 2,
    "results": [
        {
            "application": {
                "id": "674b1572-7acf-4ee5-8edb-4e241c981234",
                "code": "app11",
                "name": "app11"
            },
            "product": null
        },
        {
            "application": {
                "id": "493f0d62-9b19-4799-923b-001fb741234",
                "code": "arrluo123",
                "name": "arrluoYang"
            },
            "product": {
                "name": "arrluoYang"
            }
        }
	]
}
```

### Response Result Parameter Description

| Field |   Type | Description |
| ------ | ------ | ------ |
| count | int | Number of Apps |
| results | list | List of App information |

results
| Field |   Type | Description |
| ------ | ------ | ------ |
| application | dict | App information |
| product | dict | Product information |

application
| Field |   Type | Description |
| ------ | ------ | ------ |
| id | string | App ID |
| code | string | App code |
| name | string | App name |

product
| Field |   Type | Description |
| ------ | ------ | ------ |
| name | string | Product name |