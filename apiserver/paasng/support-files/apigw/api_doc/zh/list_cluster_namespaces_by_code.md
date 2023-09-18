### 功能描述
根据应用 ID 查询应用所在的集群和命名空间信息

### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string   | 是   | 应用 ID，如 "apigw-api-test" |

#### 2、接口参数：
暂无。

### 请求示例
```
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/applications/appid1/cluster_namespaces/
```

### 返回结果示例
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

### 返回结果参数说明

| 字段          | 类型   | 是否必填 | 描述         |
| ------------ | ------ | -------- | ------------ |
| bcs_cluster_id | string | 是       | BCS 集群 ID   |
| namespace      | string | 是       | 命名空间       |