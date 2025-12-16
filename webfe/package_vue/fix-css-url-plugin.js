/**
 * 修复 CSS 中 url() 路径的 Webpack 插件
 * 用于解决 bk-magic-vue 等第三方库的字体文件路径问题
 * 
 * 问题：CSS 中的 url() 不受 webpack_public_path.js 的影响
 * 解决：在 CSS 文件生成后，将绝对路径改为相对路径
 */
class FixCssUrlPlugin {
  constructor(options = {}) {
    this.options = {
      pattern: /url\(\s*(['"]?)\/static\/fonts\//g,
      replacement: 'url($1../fonts/',
      ...options
    };
  }

  apply(compiler) {
    const pluginName = 'FixCssUrlPlugin';
    
    compiler.hooks.emit.tapAsync(pluginName, (compilation, callback) => {
      Object.keys(compilation.assets).forEach((filename) => {
        if (!filename.endsWith('.css')) {
          return;
        }

        const asset = compilation.assets[filename];
        
        let content;
        if (typeof asset.source === 'function') {
          content = asset.source();
        } else {
          content = asset._value || asset._cachedSource;
        }
        
        if (Buffer.isBuffer(content)) {
          content = content.toString('utf-8');
        } else if (typeof content !== 'string') {
          return;
        }
        
        if (!this.options.pattern.test(content)) {
          return;
        }

        this.options.pattern.lastIndex = 0;
        
        // 将 CSS 中的绝对路径 /static/fonts/ 改为相对路径 ../fonts/
        // 例如: url(/static/fonts/xxx.ttf) => url(../fonts/xxx.ttf)
        const newContent = content.replace(
          this.options.pattern,
          this.options.replacement
        );
        
        compilation.assets[filename] = {
          source: () => newContent,
          size: () => newContent.length
        };
      });
      
      callback();
    });
  }
}

module.exports = FixCssUrlPlugin;
