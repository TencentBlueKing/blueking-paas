/**
 * 表格公共工具函数
 */

/**
 * 更新表头勾选框状态（全选/半选/未选）
 * 用于处理 bk-table 在使用 reserve-selection 时，跨页选择后表头勾选框状态不正确的问题
 *
 * @param {Object} options - 配置选项
 * @param {Object} options.tableRef - 表格组件引用 (this.$refs.xxx)
 * @param {Array} options.tableData - 当前页表格数据
 * @param {Array} options.selectedList - 已选中的数据列表
 * @param {Function} options.selectable - 判断行是否可选的函数
 * @param {String} options.rowKey - 行数据的唯一标识字段，默认 'id'
 */
export function updateHeaderCheckboxState(options) {
  const { tableRef, tableData, selectedList, selectable, rowKey = 'id' } = options;

  if (!tableRef?.store?.states) return;

  const { states } = tableRef.store;

  // 获取当前页可选择的行
  const selectableRows = tableData.filter((row) => selectable(row));
  if (!selectableRows.length) {
    states.isAllSelected = false;
    return;
  }

  // 计算当前页已选中的数量
  const selectedIds = new Set(selectedList.map((item) => getNestedValue(item, rowKey)));
  const selectedCount = selectableRows.filter((row) => selectedIds.has(getNestedValue(row, rowKey))).length;

  // 更新全选状态：只有当前页全部选中时才为 true
  states.isAllSelected = selectedCount === selectableRows.length;
}

/**
 * 获取嵌套对象的值
 * 支持 'a.b.c' 形式的路径
 *
 * @param {Object} obj - 目标对象
 * @param {String} path - 属性路径
 * @returns {*} 属性值
 */
function getNestedValue(obj, path) {
  if (!path.includes('.')) {
    return obj[path];
  }
  return path.split('.').reduce((acc, key) => acc?.[key], obj);
}
