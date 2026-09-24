# 预览联调

会话一创建就可以问预览地址。地址有了不等于页面能开，能不能看只看 `dev_server_status`。

鉴权与其它会话接口相同：平台登录，并且对这个项目有权限。iframe 会自动带上这张登录 Cookie，前端不用再塞 token。

## 问地址

`GET /api/projects/{project_id}/conversations/{number}/preview/`

```json
{
  "origin": "https://<api 主机>/api/projects/demo/conversations/3/preview/app/",
  "dev_server_status": "ready"
}
```

`origin` 末尾带斜杠，直接当作 iframe 的 `src`。会话刚建好就有，Runtime 回收后再拉起也不变。不要从 `app.launched` 里拿 url，那条事件里没有地址。

`dev_server_status` 分活着和能服务两档，照 kubernetes 的 liveness / readiness：

| 值 | 含义 | 前端 |
| --- | --- | --- |
| `null` | 没有 Runtime，或有但问不到 | 占位。这时打开 `origin` 是 503 |
| `not_started` | Runtime 在，应用还没被拉起 | 占位。打开 `origin` 多半是 502 |
| `starting` | 进程在跑，但还答不出 HTTP | 占位，并提示还在启动。继续轮询，别当失败 |
| `ready` | 约定端口应了一个 HTTP 响应 | 把 `origin` 挂上 iframe |
| `stopped` | 拉起过，进程已经没了 | 摘掉 iframe，回到占位 |

只有 `ready` 才挂 iframe。`starting` 和 `stopped` 都别报成错误：前者沙箱正在等它自己起来，后者沙箱会自动重拉，最多三次。

这个接口在 Runtime 联系不上时仍是 200，地址照常返回。

## 要轮询

没有推送。`app.launched` 只落库，不进正在进行的 `/runs` SSE，所以对话流里等不到「可以预览了」。预览面板开着的时候，前端自己打这个 GET。

- 进入这个会话的预览面板，立刻打一次，不要等第一个间隔。
- 之后每 5 秒一次，不管现在是不是 `ready`。应用拉起最多要几十秒，更密也不会更快看到页面；每次请求都会再问一次 Runtime。
- 已经挂上 iframe 之后也不要停。应用会自己掉线，没有事件通知。一旦离开 `ready`，摘掉 iframe，回到占位。
- 离开这个预览面板，或会话已结束，停止。不要在后台对每个会话一直打。

`origin` 第一次拿到就可以留下，后面只看 `dev_server_status` 变不变。

`GET .../conversations/{number}/` 的会话状态里也有 `dev_server_status`，但没有 `origin`。地址以 preview 这个接口为准。

## 打开页面

iframe 的 `src` 就是 `origin`。它后面的路径由页面自己跳，例如 `.../preview/app/docs/`。前端不要自己拼端口，也不要请求 `127.0.0.1`。

打开太早时：

- **503**：这个会话没有活着的 Runtime。
- **502**：Runtime 在，应用还没听端口。`starting` 的时候打开就是这个。

这两种都回到占位，不要把错误页留在 iframe 里。

## 联调时会对上的限制

- 预览页和控制面是同一个源。服务端用 CSP 拦住页面向平台接口发请求，也拦住它从浏览器直连第三方。应用要调外部接口，只能它自己在服务端调。
- 响应带 `X-Frame-Options: SAMEORIGIN`。前端页面必须和 API 同主机，iframe 才嵌得进去。不同源时要先改服务端，否则白屏。
- 应用若在 HTML 里写根路径资源（`/static/app.css`），会 404。相对路径和页面自己的重定向是通的。反代会带上 `X-Forwarded-Prefix`，读这条的应用能自己拼对。
- 不支持 WebSocket。用到 WS 的页面这一轮开不起来。
- 这是本机 `local_process` 的做法：流量经过 API。换成 cube 后地址和打开方式会变，iframe 不要写死这层路径以外的假设。当前可以依赖的是：`origin` 来自这个接口，`ready` 之后把它当作 `src`。
