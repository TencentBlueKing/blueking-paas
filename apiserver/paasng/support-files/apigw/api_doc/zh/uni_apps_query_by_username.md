### 功能描述
查询指定用户有权限的应用列表，仅供内部系统使用

### 请求参数

#### 1、路径参数：
暂无

#### 2、接口参数：
| 参数名称 | 类型 | 是否必填 | 描述 |
| -------- | ---- | -------- | ---- |
| username | string | 是 | 用户名 |

### 请求示例
```bash
curl -X GET -H 'X-Bkapi-Authorization: {"bk_app_code": "apigw-api-test", "bk_app_secret": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/system/uni_applications/query/by_username/?username=admin
```

### 返回结果示例
```javascript
[
    {
        "source": 1,
        "name": "蝙蝠侠",
        "code": "batman",
        "region": "default",
        "logo_url": "http://example.com/app-logo/blueking_app_default.png",
        "developers": [
            "username",
        ],
        "creator": "username",
        "created": "2019-08-13 19:15:38",
    }
]
```

### 返回结果参数说明
| 参数名称 | 类型 | 描述 |
| -------- | ---- | ---- |
| source | int | 来源 |
| name | string | 应用名称 |
| code | string | 应用代码 |
| region | string | 区域 |
| logo_url | string | 应用Logo地址 |
| developers | list | 开发者列表 |
| creator | string | 创建者 |
| created | string | 创建时间 |

**注意：已下架的应用不返回**