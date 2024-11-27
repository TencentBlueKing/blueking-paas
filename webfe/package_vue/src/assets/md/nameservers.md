本配置项可通过两种方式定义：在线表单或应用描述文件，推荐使用应用描述文件。

#### 在线表单

对于通过镜像仓库部署的应用，您可以直接在页面上添加额外的 DNS 服务器，保存后重新部署即可生效。

#### 应用描述文件

对于通过源码部署的应用，请在构建目录中的`app_desc.yaml`文件中定义`spec.domainResolution.nameservers`来添加额外的 DNS 服务器。

以下是示例文件：
```yaml
specVersion: 3
appVersion: "1.0.0"
module:
  spec:
    processes:
	  # ...已省略
    domainResolution:
        nameservers:
        - "8.8.8.8"
        - "114.114.114.114"
```

字段说明：
- `nameservers`:（array[string]）DNS 服务器地址列表，最多支持 2 条内容。

此处定义的主机列表，将和集群默认的 DNS 服务器列表合并去重后，共同生效。

> 注意：示例中的配置遵循云原生应用描述文件的最新规范（specVersion: 3）。如果您的描述文件版本为 spec_version: 2，请先将其转换为最新版本。

#### 注意事项

1. 生效范围：定义后，应用下所有模块都会生效。
2. 优先级：应用描述文件 `app_desc.yaml` 文件中如果定义了该项，则每次部署时均会刷新该配置项。