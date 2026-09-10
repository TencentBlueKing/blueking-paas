const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const sourceDir = path.join(root, 'pre-template');
const targetDir = path.join(root, 'template');

const resetTemplate = () => {
  if (!fs.existsSync(sourceDir)) {
    throw new Error(`未找到初始模板目录：${sourceDir}`);
  }

  console.log('[template] 正在从 pre-template 完整复制（含 node_modules）…');
  fs.rmSync(targetDir, { recursive: true, force: true });
  fs.cpSync(sourceDir, targetDir, {
    recursive: true,
    force: true,
    verbatimSymlinks: true,
  });
  console.log('[template] 已从 pre-template 重置');
};

module.exports = { resetTemplate };

if (require.main === module) {
  resetTemplate();
}
