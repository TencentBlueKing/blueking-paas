import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Agent, CursorAgentError } from '@cursor/sdk';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const templateDir = path.join(root, 'template');
const port = Number(process.env.AGENT_PORT || 5174);

const loadEnvLocal = () => {
  const envPath = path.join(root, '.env.local');
  if (!fs.existsSync(envPath)) return;
  for (const line of fs.readFileSync(envPath, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const index = trimmed.indexOf('=');
    if (index < 1) continue;
    const key = trimmed.slice(0, index).trim();
    const value = trimmed.slice(index + 1).trim().replace(/^['"]|['"]$/g, '');
    if (!process.env[key]) {
      process.env[key] = value;
    }
  }
};

loadEnvLocal();

const SYSTEM_PROMPT = `你正在修改 App Spark 的生成应用模板，工作目录就是这个 Vue3 + Vite 工程。
规则：
- 只改 src/ 下的页面、组件和样式
- 不要改 package.json、vite.config.ts、lockfile，不要安装新依赖
- 页面默认要能在不同宽度下正常显示，避免横向溢出；具体是桌面优先还是移动优先，按用户需求，不要擅自做成移动端优先
- 用中文简短说明你改了什么
- 改完必须能运行，预览靠 Vite 热更新`;

const IMAGE_PROMPT = `用户附带了设计稿或截图。请按图实现页面：还原布局、配色、文案、间距和层次，不要只做示意。`;

const ALLOWED_IMAGE_TYPES = new Set(['image/png', 'image/jpeg', 'image/webp', 'image/gif']);

const normalizeImages = (raw = []) => raw.slice(0, 3).flatMap((item) => {
  const mimeType = String(item?.mimeType || '');
  const source = String(item?.data || '');
  const data = source.includes(',') ? source.split(',').pop() : source;
  if (!ALLOWED_IMAGE_TYPES.has(mimeType) || !data) return [];
  return [{ data, mimeType }];
});

let agent = null;
let sending = false;

const getAgent = async () => {
  const apiKey = process.env.CURSOR_API_KEY;
  if (!apiKey) {
    throw new Error('未找到 CURSOR_API_KEY。请在 app-spark-ui/.env.local 写入 CURSOR_API_KEY=你的key');
  }
  if (!agent) {
    agent = await Agent.create({
      apiKey,
      model: { id: 'composer-2.5' },
      local: {
        cwd: templateDir,
        settingSources: [],
      },
    });
  }
  return agent;
};

const writeSse = (res, payload) => {
  res.write(`data: ${JSON.stringify(payload)}\n\n`);
};

const pickPath = (args = {}) => args.path || args.file_path || args.target_file || args.file || '';

const formatTool = (event) => {
  const name = event.name || '处理';
  const file = pickPath(event.args || {});
  const doing = event.status === 'completed' ? '已完成' : '正在';
  return file ? `${doing}${name} ${file}` : `${doing}${name}…`;
};

const isEditTool = (name = '') => /write|edit|replace|patch|delete|strreplace/i.test(name);

const appendAssistantText = (state, text, res) => {
  if (!text) return;
  if (text.startsWith(state.text)) {
    const extra = text.slice(state.text.length);
    state.text = text;
    if (extra) writeSse(res, { type: 'delta', text: extra });
    return;
  }
  if (state.text.includes(text)) return;
  state.text += text;
  writeSse(res, { type: 'delta', text });
};

const setCors = (res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');
};

const handleChat = async (req, res) => {
  const chunks = [];
  for await (const chunk of req) {
    chunks.push(chunk);
  }
  const body = JSON.parse(Buffer.concat(chunks).toString() || '{}');
  const images = normalizeImages(body.images);
  const message = String(body.message || '').trim()
    || (images.length ? '请根据附图实现页面，尽量还原布局、颜色、文案和间距。' : '');
  if (!message) {
    res.writeHead(400, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ message: 'message 不能为空' }));
    return;
  }
  if (sending) {
    res.writeHead(409, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ message: '上一条还在处理中' }));
    return;
  }

  sending = true;
  setCors(res);
  res.writeHead(200, {
    'Content-Type': 'text/event-stream',
    'Cache-Control': 'no-cache, no-transform',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no',
  });

  const assistant = { text: '' };

  try {
    const currentAgent = await getAgent();
    const prompt = `${SYSTEM_PROMPT}\n\n${images.length ? `${IMAGE_PROMPT}\n\n` : ''}用户需求：\n${message}`;
    const run = await currentAgent.send(images.length ? { text: prompt, images } : prompt, {
      local: { force: true },
      onDelta: ({ update }) => {
        if (update.type === 'text-delta' && update.text) {
          appendAssistantText(assistant, update.text, res);
        }
        if (update.type === 'thinking-delta') {
          writeSse(res, { type: 'status', text: '正在思考…' });
        }
      },
    });

    for await (const event of run.stream()) {
      if (event.type === 'assistant') {
        const text = (event.message?.content || [])
          .filter(block => block.type === 'text' && block.text)
          .map(block => block.text)
          .join('');
        appendAssistantText(assistant, text, res);
      }

      if (event.type === 'thinking') {
        writeSse(res, { type: 'status', text: '正在思考…' });
      }

      if (event.type === 'tool_call') {
        writeSse(res, { type: 'status', text: formatTool(event) });
        if (event.status === 'completed' && isEditTool(event.name)) {
          writeSse(res, { type: 'summary', items: [formatTool(event)] });
        }
      }

      if (event.type === 'task' && event.text) {
        writeSse(res, { type: 'status', text: event.text });
      }
    }

    const result = await run.wait();
    if (result.status === 'error') {
      writeSse(res, { type: 'error', text: result.error?.message || 'Agent 执行失败，请看终端日志后重试' });
    } else {
      if (!assistant.text && result.result) {
        appendAssistantText(assistant, result.result, res);
      }
      if (!assistant.text && run.supports('conversation')) {
        try {
          const turns = await run.conversation();
          const lastText = [...turns]
            .reverse()
            .flatMap(turn => turn.steps || [])
            .find(step => step.type === 'assistantMessage')
            ?.message?.text;
          if (lastText) appendAssistantText(assistant, lastText, res);
        } catch {
          // 对话记录只是兜底，不影响这次改文件结果
        }
      }
      writeSse(res, { type: 'done' });
    }
  } catch (error) {
    agent = null;
    const text = error instanceof CursorAgentError
      ? `Agent 启动失败：${error.message}`
      : (error instanceof Error ? error.message : 'Agent 服务异常');
    writeSse(res, { type: 'error', text });
  } finally {
    sending = false;
    res.end();
  }
};

const server = http.createServer((req, res) => {
  setCors(res);
  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  if (req.method === 'GET' && req.url === '/agent/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      ok: true,
      hasKey: Boolean(process.env.CURSOR_API_KEY),
      cwd: templateDir,
    }));
    return;
  }

  if (req.method === 'POST' && req.url === '/agent/chat') {
    handleChat(req, res).catch((error) => {
      if (!res.headersSent) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
      }
      res.end(JSON.stringify({ message: error.message }));
    });
    return;
  }

  res.writeHead(404);
  res.end();
});

server.listen(port, '127.0.0.1', () => {
  console.log(`[agent] listening on http://127.0.0.1:${port}`);
  console.log(`[agent] template cwd: ${templateDir}`);
  console.log(`[agent] CURSOR_API_KEY: ${process.env.CURSOR_API_KEY ? '已加载' : '未设置'}`);
});
