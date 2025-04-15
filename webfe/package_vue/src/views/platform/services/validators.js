/**
 * 校验JSON字符串是否有效（静默模式，内部打印错误）
 * @param {string} json - 要校验的JSON字符串
 * @param {object} [editorInstance=null] - 可选的编辑器实例
 * @returns {boolean} - 只返回校验结果，错误信息内部打印
 */
export function validateJson(json, editorInstance = null) {
  // 编辑器校验优先
  if (editorInstance?.validate) {
    const errors = editorInstance.validate();
    if (typeof errors === 'object') {
      console.error('JSON校验失败');
      return false;
    }
    return true;
  }
  try {
    JSON.parse(json);
    return true;
  } catch (e) {
    console.error('[JSON校验失败] 解析错误:', e.message);
    return false;
  }
};
