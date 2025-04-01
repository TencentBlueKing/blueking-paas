# 平台部署相关

## 能不能在后台触发应用部署？

平台提供了脚本指令可在后台直接部署应用, 使用方式如下:

1. 使用 apiserver 的镜像启动容器或直接进入某一个运行中的 apiserver 容器
2. 执行以下命令

```bash
# 参数说明
# --app-code [应用ID, 例如标准运维是 bk_sops]
# --module   [模块名称, 由模块自行设置的名称]
# --env      [部署环境, 可选 stag/prod, 只部署 prod 环境就填 prod 就行了]
# --revision [需要部署的版本, 对于 S-Mart 应用有两种命名规则:
#              1. 源码交付的 S-Mart 包: `package:源码包版本号`
#              2. 镜像交付的 S-Mart 包: `image:bkpaas/docker/{应用ID}/{模块名称}:{源码包版本}`

python manage.py deploy_bkapp --app-code ${应用ID} --module ${模块名称} --env prod --revision ${源码包版本}
```

## S-Mart 包只能通过页面上传吗？

平台提供了脚本指令可在后台直接上传 S-Mart 包, 使用方式如下:

1. 使用 apiserver 的镜像启动容器或直接进入某一个运行中的 apiserver 容器
2. 执行以下命令

```bash
# 参数说明
# -f [s-mart 应用包的路径]

python manage.py smart_tool -f '${S-Mart包的路径}'
```

## Redis 资源池实例只能在页面上配置吗？

平台提供了脚本指令可通过文件方式批量导入资源池的增强服务实例, 使用方式如下:

1. 使用 apiserver 的镜像启动容器或直接进入某一个运行中的 apiserver 容器
2. 执行以下命令

```bash
# 参数说明
# --service [增强服务名称, redis 增强服务的名称是 "default:redis"]
# -f        [描述实例配置的 yaml 文件路径]

python manage.py import_pre_created_instance --service "redis" -f ${实例配置文件路径}
```

### 资源池实例配置文件格式

资源池实例配置文件是一份 yaml 文件, 具有以下的字段:

- `plan`: string, 实例所属的方案名称
- `config`: string, 描述信息的附加信息的 JSON 字符串
- `credentials`： string, 描述实例的配置信息的 JSON 字符串

redis 资源池具有两个方案:

- 0shared -> 共享实例
- 1exclusive -> 独享实例

> `共享实例`不是指平台会将这个实例重复分配, 而是指运维在规划 redis 实例时, 如果希望将一个 redis 实例重复给多个 SaaS
> 使用(例如为了节约成本), 那就可以将方案设置成 `0shared`, 表示这个资源池的实例不是独享的。如果 SaaS 声明使用共享实例的
> redis, 那么由 SaaS 自行保证 redis key 不冲突   
> 另一方面, `独享实例`不应当出现**重复的实例**, 否则将可能影响 SaaS 正常运行。


以下是一份描述描述了 2 个 redis 资源池实例的样例, 其中每个样例以 `---` 为分隔符。

```yaml
plan: "0shared"
config: |
  {
      "recyclable": true
  }
credentials: |
  {
    "host": "redis-host",
    "port": 6379,
    "password": "********"
  }
---
plan: "1exclusive"
config: |
  {
      "recyclable": false
  }
credentials: |
  {
    "host": "redis-host",
    "port": 6379,
    "password": "********"
  }
```

### 如何查询资源池实例与应用的绑定关系?

平台提供了脚本指令可通过文件方式批量导入资源池的增强服务实例, 使用方式如下:

1. 使用 apiserver 的镜像启动容器或直接进入某一个运行中的 apiserver 容器
2. 执行以下命令

```bash
# 参数说明
# --service [增强服务名称, redis 增强服务的名称是 "default:redis"]
# --credentials 增强服务实例的实例配置(json format), 支持只传部分属性做模糊匹配, 
#               例如 '{"host": "xxx.xxx.xxx.xxx"}' 将匹配所有 host 为 xxx.xxx.xxx.xxx 的实例

python manage.py query_related_applications --service "default:redis" --credentials '{"host": "xxx.xxx.xxx.xxx"}'
```

如果提供的 `cretentials` 对应的资源池实例已被分配, 并且未被 SaaS 解除绑定关系, 那么执行上述指令后将会获得如下的输出:

```bash
应用名称: xxx 应用ID: xxx 模块名称: xxx 环境: xxx
```

## 环境变量只能通过页面修改吗？

平台提供了脚本指令可在后台直接导入环境变量, 使用方式如下:

1. 使用 apiserver 的镜像启动容器或直接进入某一个运行中的 apiserver 容器
2. 执行以下命令

```bash
# 参数说明
# --app-code [应用ID, 例如标准运维是 bk_sops]
# --module   [模块名称, 由模块自行设置的名称]
# -f         [环境变量的 yaml 文件路径]

python manage.py import_configvars --app-code ${应用ID} --module ${模块名称} -f ${环境变量文件路径}
```

### 环境变量文件的格式

环境变量配置文件是一份 yaml 文件, 样例如下:

```yaml
env_variables:
  - key: 环境变量的名称, 仅支持大写字母、数字、下划线
    value: 环境变量值
    environment_name: [ 环境变量生效的环境, 可选值 stag/prod/_global_, 分别对应 预发布环境/生产环境/所有环境 ]
    description: 描述文字
  - ...
```
