/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) 2017 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except
 * in compliance with the License. You may obtain a copy of the License at
 *
 *     http://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under
 * the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
 * either express or implied. See the License for the specific language governing permissions and
 * limitations under the License.
 *
 * We undertake not to change the open source license (MIT license) applicable
 * to the current version of the project delivered to anyone in the future.
 */

import i18n from '@/language/i18n';

/**
 * 函数柯里化
 *
 * @example
 *     function add (a, b) {return a + b}
 *     curry(add)(1)(2)
 *
 * @param {Function} fn 要柯里化的函数
 *
 * @return {Function} 柯里化后的函数
 */
export function curry(fn) {
  const judge = (...args) => (args.length === fn.length
    ? fn(...args)
    : arg => judge(...args, arg));
  return judge;
}

/**
 * 判断是否是对象
 *
 * @param {Object} obj 待判断的
 *
 * @return {boolean} 判断结果
 */
export function isObject(obj) {
  return obj !== null && typeof obj === 'object';
}

/**
 * 规范化参数
 *
 * @param {Object|string} type vuex type
 * @param {Object} payload vuex payload
 * @param {Object} options vuex options
 *
 * @return {Object} 规范化后的参数
 */
export function unifyObjectStyle(type, payload, options) {
  if (isObject(type) && type.type) {
    options = payload;
    payload = type;
    type = type.type;
  }

  // eslint-disable-next-line no-undef
  if (NODE_ENV !== 'production') {
    if (typeof type !== 'string') {
      console.warn(`expects string as the type, but found ${typeof type}.`);
    }
  }

  return { type, payload, options };
}

/**
 * 以 baseColor 为基础生成随机颜色
 *
 * @param {string} baseColor 基础颜色
 * @param {number} count 随机颜色个数
 *
 * @return {Array} 颜色数组
 */
export function randomColor(baseColor, count) {
  const segments = baseColor.match(/[\da-z]{2}/g);
  // 转换成 rgb 数字
  for (let i = 0; i < segments.length; i++) {
    segments[i] = parseInt(segments[i], 16);
  }
  const ret = [];
  // 生成 count 组颜色，色差 20 * Math.random
  for (let i = 0; i < count; i++) {
    ret[i] = `#${
      Math.floor(segments[0] + (Math.random() < 0.5 ? -1 : 1) * Math.random() * 20).toString(16)
    }${Math.floor(segments[1] + (Math.random() < 0.5 ? -1 : 1) * Math.random() * 20).toString(16)
    }${Math.floor(segments[2] + (Math.random() < 0.5 ? -1 : 1) * Math.random() * 20).toString(16)}`;
  }
  return ret;
}

/**
 * 异常处理
 *
 * @param {Object} err 错误对象
 * @param {Object} ctx 上下文对象，这里主要指当前的 Vue 组件
 */
export function catchErrorHandler(err, ctx) {
  const { data } = err;
  if (data) {
    if (!err.code || err.code === 404) {
      ctx.exceptionCode = {
        code: '404',
        msg: '当前访问的页面不存在',
      };
    } else if (err.code === 403) {
      ctx.exceptionCode = {
        code: '403',
        msg: 'Sorry，您的权限不足!',
      };
    } else {
      console.error(err);
      ctx.bkMessageInstance = ctx.$bkMessage({
        theme: 'error',
        message: err.message || err.data.msg || err.statusText,
      });
    }
  } else if (Object.prototype.hasOwnProperty.call(err, 'code')) {
    ctx.bkMessageInstance = ctx.$bkMessage({
      theme: 'error',
      message: err.message || err.data.msg || err.statusText,
    });
  } else {
    // 其它像语法之类的错误不展示
    console.error(err);
  }
}

/**
 * 获取字符串长度，中文算两个，英文算一个
 *
 * @param {string} str 字符串
 *
 * @return {number} 结果
 */
export function getStringLen(str) {
  let len = 0;
  for (let i = 0; i < str.length; i++) {
    if (str.charCodeAt(i) > 127 || str.charCodeAt(i) === 94) {
      len += 2;
    } else {
      // eslint-disable-next-line no-plusplus
      len++;
    }
  }
  return len;
}

/**
 * 转义特殊字符
 *
 * @param {string} str 待转义字符串
 *
 * @return {string} 结果
 */
export const escape = str => String(str).replace(/([.*+?^=!:${}()|[\]/\\])/g, '\\$1');

/**
 * 对象转为 url query 字符串
 *
 * @param {*} param 要转的参数
 * @param {string} key key
 *
 * @return {string} url query 字符串
 */
export function json2Query(param, key) {
  const mappingOperator = '=';
  const separator = '&';
  let paramStr = '';

  if (param instanceof String || typeof param === 'string'
            || param instanceof Number || typeof param === 'number'
            || param instanceof Boolean || typeof param === 'boolean'
  ) {
    paramStr += separator + key + mappingOperator + encodeURIComponent(param);
  } else {
    Object.keys(param).forEach((p) => {
      const value = param[p];
      const k = (key === null || key === '' || key === undefined)
        ? p
        : key + (param instanceof Array ? `[${p}]` : `.${p}`);
      paramStr += separator + json2Query(value, k);
    });
  }
  return paramStr.substr(1);
}

/**
 * 字符串转换为驼峰写法
 *
 * @param {string} str 待转换字符串
 *
 * @return {string} 转换后字符串
 */
export function camelize(str) {
  return str.replace(/-(\w)/g, (strMatch, p1) => p1.toUpperCase());
}

/**
 * 获取元素的样式
 *
 * @param {Object} elem dom 元素
 * @param {string} prop 样式属性
 *
 * @return {string} 样式值
 */
export function getStyle(elem, prop) {
  if (!elem || !prop) {
    return false;
  }

  // 先获取是否有内联样式
  let value = elem.style[camelize(prop)];

  if (!value) {
    // 获取的所有计算样式
    let css = '';
    if (document.defaultView && document.defaultView.getComputedStyle) {
      css = document.defaultView.getComputedStyle(elem, null);
      value = css ? css.getPropertyValue(prop) : null;
    }
  }

  return String(value);
}

/**
 *  获取元素相对于页面的高度
 *
 *  @param {Object} node 指定的 DOM 元素
 */
export function getActualTop(node) {
  let actualTop = node.offsetTop;
  let current = node.offsetParent;

  while (current !== null) {
    actualTop += current.offsetTop;
    current = current.offsetParent;
  }

  return actualTop;
}

/**
 *  获取元素相对于页面左侧的宽度
 *
 *  @param {Object} node 指定的 DOM 元素
 */
export function getActualLeft(node) {
  let actualLeft = node.offsetLeft;
  let current = node.offsetParent;

  while (current !== null) {
    actualLeft += current.offsetLeft;
    current = current.offsetParent;
  }

  return actualLeft;
}

/**
 * document 总高度
 *
 * @return {number} 总高度
 */
export function getScrollHeight() {
  let scrollHeight = 0;
  let bodyScrollHeight = 0;
  let documentScrollHeight = 0;

  if (document.body) {
    bodyScrollHeight = document.body.scrollHeight;
  }

  if (document.documentElement) {
    documentScrollHeight = document.documentElement.scrollHeight;
  }

  scrollHeight = (bodyScrollHeight - documentScrollHeight > 0) ? bodyScrollHeight : documentScrollHeight;

  return scrollHeight;
}

/**
 * 滚动条在 y 轴上的滚动距离
 *
 * @return {number} y 轴上的滚动距离
 */
export function getScrollTop() {
  let scrollTop = 0;
  let bodyScrollTop = 0;
  let documentScrollTop = 0;

  if (document.body) {
    bodyScrollTop = document.body.scrollTop;
  }

  if (document.documentElement) {
    documentScrollTop = document.documentElement.scrollTop;
  }

  scrollTop = (bodyScrollTop - documentScrollTop > 0) ? bodyScrollTop : documentScrollTop;

  return scrollTop;
}

/**
 * 浏览器视口的高度
 *
 * @return {number} 浏览器视口的高度
 */
export function getWindowHeight() {
  const windowHeight = document.compatMode === 'CSS1Compat'
    ? document.documentElement.clientHeight
    : document.body.clientHeight;

  return windowHeight;
}

/**
 * 简单的 loadScript
 *
 * @param {string} url js 地址
 * @param {Function} callback 回调函数
 */
export function loadScript(url, callback) {
  const script = document.createElement('script');
  script.async = true;
  script.src = url;

  script.onerror = () => {
    callback(new Error(`Failed to load: ${url}`));
  };

  script.onload = () => {
    callback();
  };

  document.getElementsByTagName('head')[0].appendChild(script);
}

/**
 * 根据 projectCode 获取项目
 * 获取项目 code 时，可以使用导航的项目列表 window.$projectList，因为导航的项目列表和容器服务后端的项目列表在 id, code 这块一致
 *
 * @param {string} projectCode projectCode
 *
 * @return {Object} 项目对象
 */
export function getProjectByCode(projectCode) {
  const projectList = window.$projectList || [];
  const ret = projectList.find(item => item.project_code === projectCode);
  return ret || {};
}

/**
 * 根据 projectId 获取项目
 * 获取项目 code 时，可以使用导航的项目列表 window.$projectList，因为导航的项目列表和容器服务后端的项目列表在 id, code 这块一致
 *
 * @param {string} projectId projectId
 *
 * @return {Object} 项目对象
 */
export function getProjectById(projectId) {
  const projectList = window.$projectList || [];
  const ret = projectList.find(item => item.project_id === projectId);
  return ret || {};
}

/**
 * 在当前节点后面插入节点
 *
 * @param {Object} newElement 待插入 dom 节点
 * @param {Object} targetElement 当前节点
 */
export function insertAfter(newElement, targetElement) {
  const parent = targetElement.parentNode;
  if (parent.lastChild === targetElement) {
    parent.appendChild(newElement);
  } else {
    parent.insertBefore(newElement, targetElement.nextSibling);
  }
}

/**
 * 生成UUID
 *
 * @param  {number} len 位数
 * @param  {number} radix 进制
 * @return {string} uuid
 */
export function uuid(len, radix) {
  const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'.split('');
  const uuid = [];
  let i;
  radix = radix || chars.length;
  if (len) {
    for (i = 0; i < len; i++) {
      uuid[i] = chars[0 | Math.random() * radix];
    }
  } else {
    let r;
    // eslint-disable-next-line no-multi-assign
    uuid[8] = uuid[13] = uuid[18] = uuid[23] = '-';
    uuid[14] = '4';

    for (i = 0; i < 36; i++) {
      if (!uuid[i]) {
        r = 0 | Math.random() * 16;
        uuid[i] = chars[(i === 19) ? (r & 0x3) | 0x8 : r];
      }
    }
  }

  return uuid.join('');
}

/**
 * 图表颜色
 */
export const chartColors = [
  '#2ec7c9',
  '#b6a2de',
  '#5ab1ef',
  '#fdb980',
  '#d87a80',
  '#8d98b3',
  '#e5cf0f',
  '#97b552',
  '#95706d',
  '#dc69aa',
];

/* 格式化日期
 *
 * @param  {string} date 日期
 * @param  {string} formatStr 格式
 * @return {str} 格式化后的日期
 */
export function formatDate(date, formatStr = 'YYYY-MM-DD hh:mm:ss') {
  const dateObj = new Date(date);
  const o = {
    'M+': dateObj.getMonth() + 1, // 月份
    'D+': dateObj.getDate(), // 日
    'h+': dateObj.getHours(), // 小时
    'm+': dateObj.getMinutes(), // 分
    's+': dateObj.getSeconds(), // 秒
    'q+': Math.floor((dateObj.getMonth() + 3) / 3), // 季度
    S: dateObj.getMilliseconds(), // 毫秒
  };
  if (/(Y+)/.test(formatStr)) {
    formatStr = formatStr.replace(RegExp.$1, (`${dateObj.getFullYear()}`).substr(4 - RegExp.$1.length));
  }
  for (const k in o) {
    if (new RegExp(`(${k})`).test(formatStr)) {
      formatStr = formatStr.replace(RegExp.$1, (RegExp.$1.length === 1) ? (o[k]) : ((`00${o[k]}`).substr((`${o[k]}`).length)));
    }
  }

  return formatStr;
}

/**
 * 对象数组根据指定的key去重
 *
 * @param {Array} array 原数组
 * @param {String} key
 *
 * @return {Array}
 */
export function unique(array, key) {
  if (!Array.isArray(array) || !array || array.length < 1) {
    return [];
  }
  const result = [];
  const keyList = [...new Set(array.map(item => item[key]))];
  while (keyList.length > 0) {
    for (let i = 0; i < array.length; i++) {
      const item = array[i];
      if (keyList.includes(item[key])) {
        result.push({ ...item });
        const index = keyList.findIndex(v => v === item[key]);
        keyList.splice(index, 1);
        break;
      }
    }
  }
  return result;
}

/**
 * 计算当前相对时间
 *
 * @param {string} time 日期
 *
 * @return {string} 转换后字符串
 */
export function formatTime(time) {
  const dateTimeStamp = new Date(time).getTime();
  const minute = 1000 * 60;
  const hour = minute * 60;
  const day = hour * 24;

  const month = day * 30;
  const year = month * 12;
  const now = new Date().getTime();
  const diffValue = now - dateTimeStamp;
  let result = '';
  if (diffValue < 0) {
    return;
  }
  const monthC = diffValue / month;
  const weekC = diffValue / (7 * day);
  const dayC = diffValue / day;
  const hourC = diffValue / hour;
  const minC = diffValue / minute;
  const yearC = diffValue / year;
  if (yearC >= 1) {
    return `${parseInt(yearC, 10)}${i18n.t('年前')}`;
  }
  if (monthC >= 1) {
    result = `${parseInt(monthC, 10)}${i18n.t('月前')}`;
  } else if (weekC >= 1) {
    result = `${parseInt(weekC, 10)}${i18n.t('周前')}`;
  } else if (dayC >= 1) {
    result = `${parseInt(dayC, 10)}${i18n.t('天前')}`;
  } else if (hourC >= 1) {
    result = `${parseInt(hourC, 10)}${i18n.t('小时前')}`;
  } else if (minC >= 1) {
    result = `${parseInt(minC, 10)}${i18n.t('分钟前')}`;
  } else {
    result = i18n.t('刚刚');
  }
  return result;
}

/**
 * 复制
 * @param {Object} value 复制内容
 * @param {Object} ctx 上下文对象，这里主要指当前的 Vue 组件
 */
export function copy(value, ctx) {
  const el = document.createElement('textarea');
  el.value = value;
  el.setAttribute('readonly', '');
  el.style.position = 'absolute';
  el.style.left = '-9999px';
  document.body.appendChild(el);
  const selected = document.getSelection().rangeCount > 0 ? document.getSelection().getRangeAt(0) : false;
  el.select();
  document.execCommand('copy');
  document.body.removeChild(el);
  if (selected) {
    document.getSelection().removeAllRanges();
    document.getSelection().addRange(selected);
  }
  ctx.$bkMessage({ theme: 'primary', message: ctx.$t('复制成功'), delay: 2000, dismissable: false });
}

/**
 * 检查当前元素（el）是否包含指定类名
 * @param {String} cls 类名
 * @param {Element} el 元素
 */
export function parentClsContains(cls, el) {
  if (el.classList.contains(cls)) {
    return true;
  }
  let node = el.parentNode;
  while (node) {
    if (node.classList && node.classList.contains(cls)) return true;
    node = node.parentNode;
  }
  return false;
}

/**
 * 将指定内容以.txt下载
 * @param {String} cls 类名
 * @param {Element} el 元素
 */
export function downloadTxt(content, fileName) {
  const blob = new Blob([content], { type: 'text/plain' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = fileName; // 指定下载文件的名称

  // 触发点击事件下载文件
  document.body.appendChild(link);
  link.click();

  URL.revokeObjectURL(link.href);
  document.body.removeChild(link);
}


/**
 * 将数据转为对应的层级路径
 * @param {data} Arrar 层级数据
 */
export function buildPath(data) {
  const path = [];

  // 按顺序遍历数组，将每个节点的名称添加到路径中
  data.reverse().forEach((node) => {
    const name = node.find(([key]) => key === 'name')[1];
    path.push(name);
  });

  // 返回由斜杠分隔的路径
  return path.join('/');
}

/**
 * 组织架构选择器，数据结构特殊处理
 * @param {Array} data - 原始数据
 * @param {Object} [options={}] - 配置项
 * @param {string} [options.nonUserType='department'] - 非用户类型的标识
 * @returns {Array} 标准化后的数据
 */
export function normalizeOrgSelectionData(data, options = {}) {
  const { nonUserType = 'department' } = options;
  return data.map(item => ({
    id: item.id,
    type: item.type === 'user' ? 'user' : nonUserType,
    name: item.name,
  }));
}

/**
 * 初始化一个 EventSource，以连接到服务器发送事件（SSE）流。
 * @param {string} url - 服务器端 SSE 流的 URL。
 * @param {Object} options - 事件流的配置选项。
 * @param {boolean} [options.withCredentials=false] - 是否在请求中包含凭据（如 Cookies、授权报头）。
 * @param {function} [options.onOpen=() => {}] - 连接成功建立时的回调函数。
 * @param {function} [options.onMessage=() => {}] - 处理从服务器接收消息的回调函数。
 * @param {function} [options.onError=() => {}] - 处理流期间发生错误的回调函数。
 * @param {function} [options.onEOF=() => {}] - 处理'EOF'事件的回调函数，指示流的结束。
 * @param {number} [options.reconnectInterval=5000] - 在断开连接或出错后尝试重新连接之前等待的毫秒数。
 * @param {number} [options.maxRetries=Infinity] - 最大重试次数，默认无限重试。
 * @returns {{ close: function, reconnect: function }} 返回一个包含关闭方法、重连方法的对象。
 */
export function createSSE(url, options = {}) {
  const {
    withCredentials = false,
    onOpen = () => {},
    onMessage = () => {},
    onError = () => {},
    onEOF = () => {},
    reconnectInterval = 5000,
    maxRetries = Infinity,
  } = options;

  let eventSource;
  let retryCount = 0;
  let isManuallyClosed = false;
  let reconnectTimer;

  const connect = () => {
    if (isManuallyClosed) return;

    // 清除之前的连接（如果有）
    if (eventSource) {
      eventSource.close();
    }

    eventSource = new EventSource(url, { withCredentials });

    // 连接成功建立
    eventSource.onopen = () => {
      retryCount = 0; // 重置重试计数器
      onOpen();
    };

    // 处理接收到的消息
    eventSource.onmessage = (event) => {
      onMessage(event);
    };

    // 处理错误事件
    eventSource.onerror = (error) => {
      // 仅在连接关闭时处理错误（EventSource 在重连时也会触发 error 事件）
      if (eventSource.readyState === EventSource.CLOSED) {
        onError(error, retryCount);
        if (retryCount < maxRetries) {
          retryCount += 1;
          reconnectTimer = setTimeout(connect, reconnectInterval);
        }
      }
    };

    // 处理流结束事件
    eventSource.addEventListener('EOF', () => {
      onEOF();
      close();
    });
  };

  // 开始连接
  connect();

  // 关闭连接的方法
  const close = () => {
    isManuallyClosed = true;
    clearTimeout(reconnectTimer);
    if (eventSource) {
      eventSource.close();
    }
  };

  // 主动重连的方法
  const reconnect = () => {
    isManuallyClosed = false;
    connect();
  };

  return {
    close,
    reconnect,
  };
};

