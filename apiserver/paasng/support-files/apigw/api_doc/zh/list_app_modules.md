### 功能描述
查看应用下所有的模块


### 请求参数

#### 1、路径参数：

| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| app_code | string   | 是   | 应用编码  |

#### 2、接口参数：
| 参数名称 | 参数类型 | 必须 | 参数说明 |
| -------- | -------- | ---- | -------- |
| source_origin | int   | 否   | 源码来源，目前展示所有来源。支持 1（代码仓库）、2（蓝鲸 LessCode）  |

### 请求示例
```bash
curl -X GET -H 'X-BKAPI-AUTHORIZATION: {"access_token": "your access_token"}' http://bkapi.example.com/api/bkpaas3/prod/bkapps/applications/{app_code}/modules/
```

### 返回结果示例
```json
[
    {
        "id": "4fd1848d-cd89-4bdf-ae90-423eeaccf874",
        "name": "default",
        "source_origin": 2,
        "is_default": true
    }
]
```

### 返回结果参数说明

| 字段         | 类型   | 描述       |
| ------------ | ------ | ---------- |
| id           | string | 模块 UUID  |
| name         | string | 模块名称   |
| source_origin| int    | 源码来源   |
| is_default   | bool   | 是否为默认模块 |