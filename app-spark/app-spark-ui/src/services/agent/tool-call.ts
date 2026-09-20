/**
 * 把一次工具调用压成界面上的一行。
 *
 * 参数是 AG-UI 的 TOOL_CALL_ARGS 一片片送来的 JSON 文本，调用方每收到一片就会再问一次，所以
 * 这里必须能对付只有半截的 JSON：能解析就按字段取，不能解析就用正则从里面挑出那一个关键字段，
 * 等 TOOL_CALL_END 参数齐了再算一次覆盖掉。
 */

/** 一行摘要：做什么（label） + 对什么做（detail）。 */
export interface ToolCallDisplay {
  label: string;
  detail: string;
}

/**
 * 每个已知工具挑一个最能说明「它在动什么」的参数。
 *
 * 写文件类工具（write_file / edit_file）这里只认 `path`，是刻意的：它们的 `content`、
 * `old_text`、`new_text` 动辄整个文件，摆进对话流里会把上下文冲掉，而读对话的人真正想知道的
 * 只是「它改了哪个文件」。表外的工具走通用模式，见 `genericDetail`。
 */
const TOOL_SPECS: Record<string, { label: string; key?: string }> = {
  read_file: { label: '读取文件', key: 'path' },
  write_file: { label: '写入文件', key: 'path' },
  edit_file: { label: '编辑文件', key: 'path' },
  create_directory: { label: '新建目录', key: 'path' },
  list_directory: { label: '列出目录', key: 'path' },
  file_info: { label: '查看文件', key: 'path' },
  find_files: { label: '查找文件', key: 'pattern' },
  search_files: { label: '搜索代码', key: 'pattern' },
  run_command: { label: '执行命令', key: 'command' },
  start_command: { label: '启动命令', key: 'command' },
  check_command: { label: '查看命令', key: 'command_id' },
  stop_command: { label: '停止命令', key: 'command_id' },
  read_app_log: { label: '读取应用日志' },
};

/** 一行能显示的长度，超了就截断——这里是摘要，不是日志。 */
const DETAIL_LIMIT = 72;

/**
 * 通用模式下单个参数值的长度，几个参数拼起来还得塞进 `DETAIL_LIMIT`。
 * 超过这个长度的值不再显示内容本身，见 `describeValue`。
 */
const VALUE_LIMIT = 32;

/** 压平时换行显示成这个记号，而不是悄悄变成一个空格，见 `flatten`。 */
const LINE_BREAK_MARK = ' ↵ ';

/**
 * 把一段可能有多行的文本压成一行。
 *
 * 换行不能直接当成空白抹掉：`run_command` 的参数常常是一段多行 shell，`cd build\nmake` 抹平成
 * `cd build make` 之后，摆在 `<code>` 里看着像一条能原样粘回终端的命令，而那根本不是跑过的那
 * 条。换成一个看得见的记号，读的人至少知道这里断过行。
 */
const flatten = (text: string): string => text
  .trim()
  // 先吃掉带换行的那些空白（连同换行两侧的缩进），再把剩下的横向空白并成单空格
  .replace(/\s*[\r\n]\s*/g, LINE_BREAK_MARK)
  .replace(/\s+/g, ' ');

export const clip = (text: string, limit: number): string => {
  const flat = flatten(text);
  return flat.length > limit ? `${flat.slice(0, limit)}…` : flat;
};

const parseArgs = (argsText: string): Record<string, unknown> | null => {
  const trimmed = argsText.trim();
  if (!trimmed.startsWith('{')) return null;
  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === 'object' && !Array.isArray(parsed)
      ? parsed as Record<string, unknown>
      : null;
  } catch {
    // 参数还没传完，正常情况，交给 pickString 兜底
    return null;
  }
};

/**
 * 从一段可能只有半截的 JSON 里取出某个字符串字段。
 *
 * 只认引号已经闭合的值：半个路径写在界面上比不写更糟。取不到就返回空串，等参数再长一点、或者
 * 等 TOOL_CALL_END 之后用 `parseArgs` 取准的那一份。
 *
 * 极端情况下这个值可能是从别的字段（比如某个恰好写着 `"path": "x"` 的文件内容）里误匹配来的，
 * 但参数收齐之后 `describeToolCall` 会优先用解析结果覆盖，所以最多错在流式的那几秒。
 */
const pickString = (argsText: string, key: string): string => {
  const match = new RegExp(`"${key}"\\s*:\\s*"((?:[^"\\\\]|\\\\.)*)"`).exec(argsText);
  if (!match) return '';
  try {
    return JSON.parse(`"${match[1]}"`) as string;
  } catch {
    return match[1];
  }
};

const formatValue = (value: unknown): string => (
  typeof value === 'string' ? value : String(JSON.stringify(value))
);

/**
 * 通用模式下单个值怎么显示：短的原样给，长的只报体量、不给内容。
 *
 * 不截前 `VALUE_LIMIT` 个字符，是因为表外工具压根没人替它挑过「哪个字段值得看」。agent 侧随时
 * 会加新工具，一旦加了个带 `content`、`patch` 这类大字段的工具又忘了回这里补 `TOOL_SPECS`，截
 * 断就等于把文件开头（可能是密钥，可能是用户数据）原样贴进对话流——而那几十个字符本来也说明
 * 不了什么。报个「<1024 字符>」既不泄内容，也足够让人看出这里该去补一条工具声明了。
 */
const describeValue = (value: unknown): string => {
  const flat = flatten(formatValue(value));
  return flat.length > VALUE_LIMIT ? `<${flat.length} 字符>` : flat;
};

/** 表外工具的裸展示：把参数摊成 `key=value`，每个值交给 `describeValue` 掐短。 */
const genericDetail = (argsText: string): string => {
  const args = parseArgs(argsText);
  if (!args) return '';
  return Object.entries(args)
    .map(([key, value]) => `${key}=${describeValue(value)}`)
    .join('  ');
};

/**
 * 算出一次工具调用该显示成什么。
 *
 * @param name AG-UI 的 toolCallName
 * @param argsText 到目前为止收到的参数 JSON，允许不完整
 */
export const describeToolCall = (name: string, argsText: string): ToolCallDisplay => {
  const spec = TOOL_SPECS[name];
  if (!spec) {
    return { label: name || '调用工具', detail: clip(genericDetail(argsText), DETAIL_LIMIT) };
  }
  if (!spec.key) {
    return { label: spec.label, detail: '' };
  }
  const parsed = parseArgs(argsText)?.[spec.key];
  const value = typeof parsed === 'string' ? parsed : pickString(argsText, spec.key);
  return { label: spec.label, detail: clip(value, DETAIL_LIMIT) };
};
