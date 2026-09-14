const { spawn } = require('child_process');
const path = require('path');
const { resetTemplate } = require('./reset-template');

const root = path.resolve(__dirname, '..');
const children = [];

resetTemplate();

const run = (command, args, cwd) => {
  const child = spawn(command, args, {
    cwd,
    stdio: 'inherit',
    shell: true,
    env: process.env,
  });
  children.push(child);
};

run('node', ['./scripts/agent-server.mjs'], root);
run('npm', ['run', 'dev'], path.join(root, 'template'));
run('npx', ['bk-cli-service-webpack', 'dev'], root);

const shutdown = () => {
  children.forEach((child) => {
    if (!child.killed) {
      child.kill();
    }
  });
};

process.on('SIGINT', () => {
  shutdown();
  process.exit(0);
});

process.on('SIGTERM', () => {
  shutdown();
  process.exit(0);
});
