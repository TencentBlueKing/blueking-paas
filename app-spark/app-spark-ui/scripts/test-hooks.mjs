/**
 * `node --test` 的模块解析钩子，用 `--import` 加载。
 *
 * 源码按 webpack 的规矩写：`@/` 指向 src，相对路径不带扩展名。node 自己不认这两样，这里补上；
 * 顺带把发请求、弹窗的模块换成 src/test-support 里的替身，store 才能脱离浏览器跑起来。
 */
import { statSync } from 'node:fs';
import { registerHooks } from 'node:module';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const src = fileURLToPath(new URL('../src/', import.meta.url));

const stubs = {
  '@/http/api': 'test-support/http-api.ts',
  '@/common/message': 'test-support/message.ts',
};

const isFile = (file) => statSync(file, { throwIfNoEntry: false })?.isFile() ?? false;

const findSource = (base) => [base, `${base}.ts`, path.join(base, 'index.ts')].find(isFile);

registerHooks({
  resolve(specifier, context, nextResolve) {
    if (stubs[specifier]) {
      return { url: pathToFileURL(path.join(src, stubs[specifier])).href, shortCircuit: true };
    }
    let base;
    if (specifier.startsWith('@/')) {
      base = path.join(src, specifier.slice(2));
    } else if (specifier.startsWith('.') && context.parentURL?.startsWith('file:')) {
      const parent = fileURLToPath(context.parentURL);
      if (parent.startsWith(src)) base = path.resolve(path.dirname(parent), specifier);
    }
    const file = base && findSource(base);
    if (file) return { url: pathToFileURL(file).href, shortCircuit: true };
    return nextResolve(specifier, context);
  },
});
