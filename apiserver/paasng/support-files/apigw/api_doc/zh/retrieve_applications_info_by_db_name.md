### 功能描述
根据 mysql 增强服务实例的数据库名称查询所属应用的基本信息

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| db_name   | string | 是 | 数据库名称 |

#### 2、接口参数：
暂无。

### 请求示例
```
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bkapps/services/mysql/{db_name}/related_applications_info/
```

### 返回结果示例
```
{
    "id": "d53450b6-fd5b-49b6-883f-e64030377a52",
    "code": "bk_app_codexxxx",
    "name": "应用名称",
    "administrators": [
        "admin"
    ],
    "devopses": [
        "admin2"
    ],
    "developers": [
        "admin1"
    ],
    "last_operator": "admin1"
}
```

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| id | string | 应用ID |
| code | string | 应用编码 |
| name | string | 应用名称 |
| administrators | list | 应用管理员 |
| devopses | list | DevOps人员 |
| developers | list | 开发人员 |
| last_operator | string | 最后操作人 |