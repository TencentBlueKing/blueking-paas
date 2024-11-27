本配置项可通过两种方式定义：在线表单或应用描述文件，推荐使用应用描述文件。

#### 在线表单
对于通过镜像仓库部署的应用，您可以直接在页面配置服务发现，保存后重新部署即可生效。

#### 应用描述文件
对于通过源码部署的应用，请在构建目录中的`app_desc.yaml`文件中定义`spec.svcDiscovery.bkSaaS` 字段以实现服务发现，从而获取蓝鲸平台上其他应用的访问地址。

以下是示例文件：
```yaml
specVersion: 3
appVersion: "1.0.0"
module:
  spec:
    processes:
    # ...已省略
    svcDiscovery:
      bkSaaS:
        - bkAppCode: bk-iam
        - bkAppCode: bk-user
          moduleName: api
```

服务发现定义字段 spec.svcDiscovery.bkSaaS，类型为数组结构：
- `bkAppCode`: (必填，string) 蓝鲸应用的 Code。
- `moduleName`: (可选，string) 应用的模块名称。如果不设置，表示“主模块”（即 `isDefault` 为 True 的模块）。

如果只需获取应用的主访问地址，而不关注具体模块，建议不要指定 `moduleName` 字段。

> 注意：示例中的配置遵循云原生应用描述文件的最新规范（specVersion: 3）。如果您的描述文件版本为 spec_version: 2，请先将其转换为最新版本。

#### 注意事项
1. 生效范围：定义后，应用下所有模块都会生效。
2. 优先级：应用描述文件 `app_desc.yaml` 文件中如果定义了该项，则每次部署时均会刷新该配置项。
