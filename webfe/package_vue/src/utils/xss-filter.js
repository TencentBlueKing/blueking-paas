import xss from 'xss';

/**
 * 默认 XSS 过滤配置 - 纯文本
 */
const defaultXssOptions = {
  whiteList: {}, // 默认清空所有 HTML 标签
  stripIgnoreTag: true, // 过滤所有非白名单标签
  stripIgnoreTagBody: ['script', 'style'], // 特别处理 script 和 style 标签
};

/**
 * 危险属性列表（事件处理器等）
 */
const DANGEROUS_ATTRS = [
  'onload',
  'onerror',
  'onmouseover',
  'onmouseout',
  'onclick',
  'ondblclick',
  'onmousedown',
  'onmouseup',
  'onmousemove',
  'onfocus',
  'onblur',
  'onchange',
  'onsubmit',
  'onreset',
  'onselect',
  'onkeydown',
  'onkeypress',
  'onkeyup',
  'onabort',
  'oncanplay',
  'oncanplaythrough',
  'oncuechange',
  'ondurationchange',
  'onemptied',
  'onended',
  'onloadeddata',
  'onloadedmetadata',
  'onloadstart',
  'onpause',
  'onplay',
  'onplaying',
  'onprogress',
  'onratechange',
  'onseeked',
  'onseeking',
  'onstalled',
  'onsuspend',
  'ontimeupdate',
  'onvolumechange',
  'onwaiting',
  'onafterprint',
  'onbeforeprint',
  'onbeforeunload',
  'onerror',
  'onhashchange',
  'onload',
  'onmessage',
  'onoffline',
  'ononline',
  'onpagehide',
  'onpageshow',
  'onpopstate',
  'onresize',
  'onstorage',
  'onunload',
  'onbegin',
  'onend',
  'onrepeat',
  'onfocusin',
  'onfocusout',
  'onactivate',
  'onclick',
  'oncontextmenu',
  'ondrag',
  'ondragend',
  'ondragenter',
  'ondragleave',
  'ondragover',
  'ondragstart',
  'ondrop',
  'onmousewheel',
  'onscroll',
  'onwheel',
  'oncopy',
  'oncut',
  'onpaste',
];

/**
 * 富文本 XSS 过滤配置
 */
const richTextXssOptions = {
  whiteList: {
    // 重新定义白名单，不继承 xss.whiteList 以确保更严格的控制
    p: ['class', 'style'],
    span: ['class', 'style'],
    div: ['class', 'style'],
    h1: ['class', 'style'],
    h2: ['class', 'style'],
    h3: ['class', 'style'],
    h4: ['class', 'style'],
    h5: ['class', 'style'],
    h6: ['class', 'style'],
    strong: [],
    b: [],
    em: [],
    i: [],
    u: [],
    s: [],
    blockquote: ['class', 'style'],
    ul: ['class', 'style'],
    ol: ['class', 'style'],
    li: ['class', 'style'],
    br: [],
    a: ['href', 'title', 'target', 'rel', 'class', 'style'],
    img: ['src', 'alt', 'title', 'width', 'height', 'class', 'style'],
    table: ['class', 'style', 'border', 'cellspacing', 'cellpadding'],
    thead: ['class', 'style'],
    tbody: ['class', 'style'],
    tr: ['class', 'style'],
    th: ['class', 'style', 'colspan', 'rowspan'],
    td: ['class', 'style', 'colspan', 'rowspan'],
    code: ['class'],
    pre: ['class'],
  },
  stripIgnoreTag: true,
  stripIgnoreTagBody: ['script', 'style', 'iframe', 'object', 'embed', 'link'],
  onTagAttr: (tag, name, value, isWhiteAttr) => {
    // 拒绝所有危险属性
    if (DANGEROUS_ATTRS.includes(name.toLowerCase())) {
      return '';
    }

    // 只允许白名单中明确定义的属性
    if (!isWhiteAttr) {
      return '';
    }

    // 安全处理 href 属性
    if (tag === 'a' && name === 'href') {
      const protocol = value.split(':')[0].toLowerCase();
      if (!['http', 'https', 'mailto', 'tel'].includes(protocol)) {
        return '';
      }
      // 检查是否包含危险的 javascript: 等协议
      if (value.toLowerCase().includes('javascript:') || value.toLowerCase().includes('vbscript:')) {
        return '';
      }
      return `${name}="${xss.escapeAttrValue(value)}"`;
    }

    // 处理图片 src 属性 - 只允许 base64 图片
    if (tag === 'img' && name === 'src') {
      // 只允许 base64 图片
      if (value.startsWith('data:image/')) {
        const [header] = value.split(',');
        const imageType = header.match(/^data:image\/(\w+);base64$/);
        if (imageType && ['png', 'jpeg', 'jpg', 'gif', 'webp', 'svg+xml'].includes(imageType[1])) {
          // 检查 base64 数据是否过大（防止 DoS 攻击）
          if (value.length > 2 * 1024 * 1024) {
            // 2MB 限制
            return '';
          }
          return `${name}="${xss.escapeAttrValue(value)}"`;
        }
      }
      // 拒绝所有非 base64 图片
      return '';
    }

    // 处理样式属性 - 更严格的验证
    if (name === 'style') {
      const safeStyles = [
        'color',
        'background-color',
        'font-size',
        'font-family',
        'font-weight',
        'text-align',
        'text-decoration',
        'margin',
        'margin-top',
        'margin-right',
        'margin-bottom',
        'margin-left',
        'padding',
        'padding-top',
        'padding-right',
        'padding-bottom',
        'padding-left',
        'border',
        'border-width',
        'border-style',
        'border-color',
        'width',
        'height',
        'max-width',
        'max-height',
        'line-height',
      ];

      // 检查是否包含危险的 CSS 内容
      const dangerousPatterns = [
        /javascript:/i,
        /expression\s*\(/i,
        /url\s*\(/i, // 禁止 CSS 中的 url() 函数
        /@import/i,
        /behavior\s*:/i,
        /-moz-binding/i,
      ];

      if (dangerousPatterns.some((pattern) => pattern.test(value))) {
        return '';
      }

      // 验证每个样式属性
      const styles = value.split(';').filter((s) => s.trim());
      const validStyles = styles.filter((style) => {
        const [prop] = style.split(':').map((s) => s.trim());
        return safeStyles.includes(prop.toLowerCase());
      });

      if (validStyles.length !== styles.length) {
        // 如果有不安全的样式，过滤掉
        const cleanValue = validStyles.join(';');
        return cleanValue ? `${name}="${xss.escapeAttrValue(cleanValue)}"` : '';
      }

      return `${name}="${xss.escapeAttrValue(value)}"`;
    }

    // 对于其他属性，只允许白名单属性并进行额外验证
    return `${name}="${xss.escapeAttrValue(value)}"`;
  },
  safeAttrValue: (tag, name, value, cssFilter) => {
    // 额外安全处理
    if (name === 'class') {
      // 防止 CSS 注入，只允许安全字符
      return value.replace(/[^a-z0-9-_ ]/gi, '');
    }

    // 对所有属性值进行额外的安全检查
    const dangerousPatterns = [
      /javascript:/i,
      /vbscript:/i,
      /data:/i, // 除了图片的 data: 协议
      /file:/i,
      /&#/i, // HTML 实体编码
      /&[a-z]+;/i, // HTML 实体
    ];

    // 对于非 img 标签的 src 属性或非 data:image 的情况，检查危险模式
    if (!(tag === 'img' && name === 'src' && value.startsWith('data:image/'))) {
      if (dangerousPatterns.some((pattern) => pattern.test(value))) {
        return '';
      }
    }

    return xss.safeAttrValue(tag, name, value, cssFilter);
  },
  onTag: (tag) => {
    // 完全禁止某些危险标签
    const forbiddenTags = [
      'script',
      'iframe',
      'object',
      'embed',
      'form',
      'input',
      'textarea',
      'button',
      'select',
      'option',
      'link',
      'meta',
      'base',
    ];
    if (forbiddenTags.includes(tag)) {
      return '';
    }
  },
};

/**
 * 自定义 XSS 过滤器
 * @param {string} content - 要过滤的内容
 * @param {Object} options - 自定义过滤选项
 * @returns {string} - 过滤后的内容
 */
export function filterXss(content, options = {}) {
  if (!content || typeof content !== 'string') {
    return content;
  }

  const mergedOptions = {
    ...defaultXssOptions,
    ...options,
  };

  return xss(content, mergedOptions);
}

/**
 * 过滤纯文本内容（去除所有 HTML 标签）
 * @param {string} content - 要过滤的内容
 * @returns {string} - 过滤后的纯文本
 */
export function filterPlainText(content) {
  return filterXss(content);
}

/**
 * 过滤富文本内容（允许安全的 HTML 标签和属性）
 * @param {string} content - 要过滤的富文本内容
 * @param {Object} customOptions - 自定义富文本过滤选项
 * @returns {string} - 过滤后的富文本
 */
export function filterRichText(content, customOptions = {}) {
  const options = {
    ...richTextXssOptions,
    ...customOptions,
  };
  return filterXss(content, options);
}

/**
 * 递归过滤对象或数组中的所有字符串值
 * @param {Object|Array} data - 要过滤的数据
 * @param {Function} filterFn - 过滤函数
 * @returns {Object|Array} - 过滤后的数据
 */
export function deepFilterXss(data, filterFn = filterPlainText) {
  if (!data) return data;

  if (typeof data === 'string') {
    return filterFn(data);
  }

  if (Array.isArray(data)) {
    return data.map((item) => deepFilterXss(item, filterFn));
  }

  if (typeof data === 'object') {
    const result = {};
    for (const key in data) {
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        result[key] = deepFilterXss(data[key], filterFn);
      }
    }
    return result;
  }

  return data;
}

/**
 * 验证图片 URL 是否安全（仅允许 base64 图片）
 * @param {string} url - 图片 URL
 * @returns {boolean} - 是否安全
 */
export function isValidImageUrl(url) {
  if (!url || typeof url !== 'string') {
    return false;
  }

  // 只允许 base64 图片
  if (url.startsWith('data:image/')) {
    const [header] = url.split(',');
    const imageType = header.match(/^data:image\/(\w+);base64$/);
    return imageType && ['png', 'jpeg', 'jpg', 'gif', 'webp', 'svg+xml'].includes(imageType[1]);
  }

  // 拒绝所有其他格式
  return false;
}
