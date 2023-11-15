### 功能描述
部署云原生应用。

### 请求参数

#### 1、路径参数：

|   参数名称   |    参数类型  |  必须  |     参数说明     |
| ------------ | ------------ | ------ | ---------------- |
| app_code   | string | 是 | 应用 ID |
| module   | string | 是 | 模块名称，如 "default" |
| env | string | 是 | 环境名称，可选值 "stag" / "prod" |

#### 2、接口参数：

| 字段 |   类型 |  是否必填 | 描述 |
| ------ | ------ | ------ | ------ |
| manifest | object | 是 | 云原生应用的应用模型 Json 对象 |


### 请求示例

```json
{
  "manifest": {
    "apiVersion": "paas.bk.tencent.com/v1alpha1",
    "kind": "BkApp",
    "spec": {
      "processes": [
        {
          "cpu": "1000m",
          "args": [],
          "name": "web",
          "image": "nginx:latest",
          "memory": "256Mi",
          "command": [],
          "replicas": 1,
          "targetPort": 80
        }
      ],
      "configuration": {
        "env": []
      }
    }
  }
}
```

#### 获取你的 access_token

在调用接口之前，请先获取你的 access_token，具体指引请参照 [使用 access_token 访问 PaaS V3](https://bk.tencent.com/docs/markdown/PaaS/DevelopTools/BaseGuide/topics/paas/access_token)

### 返回结果示例

```json
{
  "apiVersion": "paas.bk.tencent.com/v1alpha1",
  "kind": "BkApp",
  "metadata": {
    // 资源元信息，内容省略
  },
  "spec": {
    // 应用模型配置，内容省略
  },
  "status": {
    // 资源当前状态，内容省略
  }
}
```

### 返回结果参数说明

| 字段 |   类型 | 描述 |
| ------ | ------ | ------ |
| apiVersion | string | API 版本 |
| kind | string | 资源类型 |
| metadata | object | 资源元信息 |
| spec | object | 应用模型配置 |
| status | object | 资源当前状态 |