# Webfe

## 本地开发环境搭建

> 推荐 nodejs 版本: v14.17.6

### 安装依赖包

```shell
# 假设你目前在 webfe/package_vue 目录下
npm install
```

**注：如果遇到 webpack 版本错误，请移除现有环境（node_modules），重新安装依赖**

### 配置 host

```shell
127.0.0.1 bkpaas-dev.example.com（看具体环境使用的域名）
```

### 配置环境变量

```shell
# apiserver 模块的域名
export BK_PAAS3_URL="http://bkpaas.example.com"
# 登录服务地址
export BK_LOGIN_URL="http://paas.example.com/login"
```

### 启动服务

```shell
# 版本代号: te 代表腾讯内部版本、ee 代表外部版本
# 如果运行 te 版本，需要在 package_vue 目录下添加 webfe-settings
npm run dev:${版本代号}
```

### 如何访问

启动后，本地访问地址示例 `http://bkpaas-dev.example.com:{port}`, 其中 `port` 的值配置在 `webfe/package_vue/config/index.js` 中

## 打包与构建

### 打包静态文件

```shell
# 版本代号: te 代表腾讯内部版本、ee 代表外部版本
npm run build:${版本代号}
```

命令执行完成后在项目根目录生成 `dist` 目录，包括前端运行的 `js`、`css` 等资源

### 镜像构建

```bash
docker build --network host -f Dockerfile . -t mirrors.tencent.com/blueking/webfe:${tag}
```
