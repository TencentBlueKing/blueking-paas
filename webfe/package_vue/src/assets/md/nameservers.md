#### 操作说明

打开位于构建目录中的`app_desc.yaml`文件，定义`spec.domainResolution.nameservers`来添加额外的 DNS 服务器。一份示例文件如下所示： 

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

**说明**：此处定义的主机列表，将和集群默认的 DNS 服务器列表合并去重后，共同生效
