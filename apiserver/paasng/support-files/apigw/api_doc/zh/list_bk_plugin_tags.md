### 功能描述
查询蓝鲸插件的分类列表，仅供内部系统使用。

### 请求参数

#### 1、路径参数：
暂无

#### 2、接口参数：
暂无

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "bk_apigw_test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/bk_plugin_tags
```

### 返回结果示例
```javascript
[
    {
        "code_name": "tag1",
        "name": "分类1",
        "id": 1
    }
]
```

### 返回结果参数说明

| 字段      | 类型   | 描述   |
| --------- | ------ | ------ |
| code_name | string | 分类编码 |
| name      | string | 分类名称 |
| id        | int    | 分类ID  |