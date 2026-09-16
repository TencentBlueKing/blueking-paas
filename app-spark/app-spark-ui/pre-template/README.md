# App Spark SaaS 前端模板

生成应用使用的 Vue 3 + Vite 薄内核。平台锁定构建链和 SDK，业务代码写在 `src/pages`。

## 本地运行

```bash
cd app-spark-ui/templates/vue3-vite-app
npm install
npm run dev
```

浏览器打开终端输出的地址（默认 `http://localhost:5173`）。

## 目录约定

| 路径 | 说明 |
|---|---|
| `src/platform/` | 请求、登录等平台 SDK，预览/部署时由平台注入，不要改启动方式 |
| `src/pages/` | 业务页面（对话生成与完善的主目录） |
| `src/router/index.ts` | 路由表，加页时在这里注册 |
| `package.json` | 依赖已预装，默认不要改 |

`bkui-vue` 已安装，管理台页面可直接用；游戏等自定义页也可以不用。
