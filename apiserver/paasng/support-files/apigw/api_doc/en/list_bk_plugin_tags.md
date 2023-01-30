### Resource Description

Query logs for a blueking plug-in tags for internal system use only.


### Authentication mode

Use Bearer method for authentication. Please apply to the administrator for specific authentication.

### Input parameter Description

|   Field   | Type | Required |     Description     |
| ------------ | ------------ | ------ | ---------------- |
| private_token | string      | no  | Token allocated by PaaS platform, which must be provided when the app identity of the requester is not authenticated by PaaS platform |


### Return result

```javascript
[
    {
        "code_name": "tag1",
        "name": "分类1",
        "id": 1
    }
]
```