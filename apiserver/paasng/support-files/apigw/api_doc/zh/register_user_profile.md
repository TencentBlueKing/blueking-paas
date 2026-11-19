### 功能描述
为当前用户在开发者中心注册。用户首次通过浏览器访问开发者中心时会自动注册，从未访问过开发者中心的用户可通过本接口预先注册，之后才能被设置为应用管理员。

必须以用户身份调用，注册的用户及其所属租户都取自网关认证的用户，不能替其他用户注册。重复调用不会修改已有的注册信息，直接返回。

平台关闭了自助注册时返回 403，需由平台管理员手动添加用户。

### 请求参数

#### 1、路径参数：
暂无。

#### 2、接口参数：
暂无。

### 请求示例
```
curl -X POST -H 'x-bkapi-authorization: {"bk_app_code": "app-spark", "bk_app_secret": "***", "access_token": "***"}' --insecure https://bkapi.example.com/api/bkpaas3/prod/accounts/user_profile/
```

### 返回结果示例
```
{
    "username": "admin",
    "tenant_id": "default",
    "role": 2
}
```

### 返回结果参数说明

| 字段 | 类型 | 描述 |
| ------ | ------ | ------ |
| username | string | 用户名 |
| tenant_id | string | 用户所属租户 ID |
| role | int | 用户在开发者中心的角色，2 为普通用户 |
