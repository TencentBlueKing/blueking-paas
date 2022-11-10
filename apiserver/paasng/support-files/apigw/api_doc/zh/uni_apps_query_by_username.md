### 资源描述

查询指定用户有权限的应用列表，仅供内部系统使用

### 认证方式

使用 Bearer 方式认证，具体的 token 请向管理员申请。

### 输入参数说明
| 参数名称      | 参数类型     | 必须 | 参数说明                           |
|---------------|--------------|-----|--------------------------------|
| private_token | string       | 否   | PaaS 平台分配的 token,当请求方的应用身份未被 PaaS 平台认证时必须提供|
| username      | string | 是   | 用户名|

### 返回结果

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

### 返回结果说明

- 已下架的应用不返回