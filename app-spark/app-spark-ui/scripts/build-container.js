const { spawnSync } = require('node:child_process');
const { resolve } = require('node:path');

// customEnv 在 CLI 中覆盖普通生产变量，无需改写 PaaS 的配置文件。
const result = spawnSync('npm', ['run', 'build'], {
  cwd: resolve(__dirname, '..'),
  stdio: 'inherit',
  env: { ...process.env, APP_SPARK_CONTAINER_BUILD: '1' },
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
