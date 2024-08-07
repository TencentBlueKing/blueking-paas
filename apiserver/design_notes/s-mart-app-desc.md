# S-Mart 应用和应用描述文件

本文档包含一些与S-Mart 应用和应用描述文件有关的全局视角的代码设计笔记。

## 基础概念

名词解释：

- S-Mart 应用：一种特殊的应用类型，一个 S-Mart 应用由一个包含源码与*描述文件*的压缩包组成，可被上传至开发者中心完成应用创建和版本更新；
- 描述文件：存放在源码根目录（或“构建目录”）的名为 `app_desc.yaml` 的 YAML 配置文件，其中包含各模块的进程定义、服务发现配置等内容。

一份示例的描述文件（版本 2）如下所示：

```YAML
spec_version: 2
module:
  language: Python
  processes:
    web:
      command: gunicorn wsgi -w 4 -b :$PORT --access-logfile - --error-logfile - --access-logformat '[%(h)s] %({request_id}i)s %(u)s %(t)s "%(r)s" %(s)s %(D)s %(b)s "%(f)s" "%(a)s"'
  svc_discovery:
    bk_saas:
        - 'bksops'
```

### 常见技术概念

### 多种描述文件版本

历经多次迭代后，应用描述文件目前支持多种不同格式版本，当前在使用的主要为版本 2 和版本 3。其中，版本 2 启用时间较早，支持的字段数量有限，常被用来描述进程信息，所有字段名采用蛇形命名法（field_name）。版本 3 是最新版，其中的 Spec 字段使用和 SaaS 应用模型（BkApp）完全一致的格式，命名为驼峰式（fieldName）。

> 问：为什么版本 3 的 Spec 使用  BkApp 模型规范？
> 
> 主要原因在于 BkApp 应用模型已具备完善的描述能力，且在不断迭代更新中，复用该模型定义能有效降低用户理解成本和平台的维护成本。

在代码实现层面上，虽然不同版本的描述文件格式不一，在经由数据校验层后会被统一转换为 BkApp 内部数据模型，这主要是为了简化后端逻辑的编写。

> 附：版本 2 的数据模型转换逻辑 [validations/v2.py](https://github.com/TencentBlueKing/blueking-paas/blob/9d8ccab3cd6e376513cb3166bc4db2ae2134c79d/apiserver/paasng/paasng/platform/declarative/deployment/validations/v2.py#L152)。

### Procfile 和 app_desc.yaml

平台早期曾建议应用使用 Procfile 文件来定义进程，之后改为描述文件 app_desc.yaml。相比 Procfile，描述文件支持更多更复杂的字段，支持定义进程副本数、健康探针等配置项。

为了保证向前兼容，平台在读取完 app_desc.yaml 中的进程数据后，仍会试着去解析 Procfile 中的内容。假如数据冲突，以 Procfile 中的内容为准。

### 应用描述文件的生效时间点

应用描述文件主要在应用的构建阶段生效。构建时，平台读取文件内容，将其中的各类模型数据存储到库中。对于不同类型的应用，处理逻辑稍有不同：

- 云原生应用：各配置项持久化到对应模型中，如进程被写入 ModuleProcessSpec，钩子命令写入 ModuleDeployHook，以便部署时基于它们生成 BkApp YAML**（此 YAML 生成流程对于未使用描述文件的应用同样适用）**
- 普通应用：同云原生应用逻辑类似，但未使用粗放的“完全导入整个 Spec”方式，而是分别同步各类数据

除此之外，文件中的原始 Spec 内容也会被存放到本次部署所对应的 DeploymentDescription 模型中。其中的部分字段，在应用部署进行到后期时，仍可能被独立读取并使用，比如 [spec.svsDiscovery 会被用来合并环境读取](https://github.com/TencentBlueKing/blueking-paas/blob/main/apiserver/paasng/paasng/platform/declarative/models.py#L74)（*该行为未来可能需要优化，比如使用 SvcDiscConfig 模型？*）。

> 疑问：DeploymentDescription 可能需要更清晰的职责和定位，比如是仅仅用作归档 Spec 数据，还是具备一些实际的业务功能（如前面提到的 spec.svcDiscovery）。

### 描述文件：解析、分解和再还原

对于那些采用版本 3 描述文件的应用，描述文件功能的整个生效过程遵循“解析、分解和再还原”的模式。

1. 解析：开发者在仓库中按 BkApp 规范编写 app_desc.yaml，其中的 Spec 字段被平台 declarative 模块解析；
2. 分解：Spec 首先被作为一个 BkApp 整体理解，然后各类型数据被分散持久化到多种数据库模型中；
3. 还原：当应用将被部署到集群前，平台读取各类数据，调用 `get_bkapp_resource()` 将其拼装为 BkApp 资源 YAML（可被提交到集群）。

此过程中，一些需要额外关注的细节：

- 最终的 BkApp 资源 YAML，同最初在描述文件中定义的虽然内容相似，但并不完全一致，比方说前者会多出一些系统内置（或增强服务）环境变量；
- “分解”过程也不能和“导入 BkApp YAML”划等号，比如，环境变量并不会被写入到 ConfigVar 中，而是存放在 PresetEnvVariable 模型里。

### 预设环境变量（PresetEnvVariable）

预设环境变量是一类特殊的环境变量，所使用的模型名为 `PresetEnvVariable`。虽然定位与普通环境变量类似，但 `PresetEnvVariable` 只被用来存放那些经由应用描述文件（`app_desc.yaml`）定义的变量，开发者无法通过环境变量 web 页面管理它们。

在应用部署时，预设环境变量会被合并到最终的 BkApp 资源 YAML 中。
