组件管理器用于管理平台支持的各类组件及其不同版本
包括组件的模板定义、参数 Schema、文档等信息

```
目录结构说明：
   components/
   ├── cl5/                 # cl5 类型组件
   │   ├── v1/              # v1版本
   │   │   ├── template.yaml  # 组件部署模板
   │   │   ├── schema.json    # 组件参数 Schema 定义
   │   │   └── docs.md        # 组件详细文档说明
   │   └── v2/              # v2版本
   │       ├── template.yaml
   │       ├── schema.json
   │       └── docs.md
   ├── env_overlay/              # env_overlay 类型组件
   │   ├── v1/
   │   │   ├── template.yaml
   │   │   ├── schema.json
   │   │   └── docs.md
   │   └── v2/
   │       ├── template.yaml
   │       ├── schema.json
   │       └── docs.md
```

主要功能：
  - 组件信息的加载与管理
  - 组件模板的获取
  - 组件参数 Schema 的验证