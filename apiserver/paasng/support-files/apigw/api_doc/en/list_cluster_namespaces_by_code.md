### Description
Query the cluster and namespace information of the application based on the application ID

### Request Parameters

#### 1. Path Parameters:

| Parameter Name | Parameter Type | Required | Description |
| -------------- | -------------- | -------- | ----------- |
| code       | string         | Yes      | Application ID, e.g. "apigw-api-test" |

#### 2. API Parameters:
None.

### Request Example
```
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/appid1/cluster_namespaces/
```

### Response Example
```
[
    {
        "bcs_cluster_id": "BCS-K8S-40104",
        "namespace": "bkapp-appid1-stag"
    },
    {
        "bcs_cluster_id": "BCS-K8S-40104",
        "namespace": "bkapp-appid1-prod"
    },
]
```

### Response Parameters Description

| Field          | Type   | Required | Description      |
| -------------- | ------ | -------- | ---------------- |
| bcs_cluster_id | string | Yes      | BCS Cluster ID   |
| namespace      | string | Yes      | Namespace        |