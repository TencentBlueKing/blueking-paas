/*
 * TencentBlueKing is pleased to support the open source community by making
 * 蓝鲸智云 - PaaS 平台 (BlueKing - PaaS System) available.
 * Copyright (C) Tencent. All rights reserved.
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

import ExcelJS from 'exceljs';
import { saveAs } from 'file-saver';

/**
 * 从 HTML 表格生成数据数组
 * @param {HTMLElement} table - 表格元素
 * @returns {Array} 表格数据数组
 */
function generateArray(table) {
  const out = [];
  const rows = table.querySelectorAll('tr');
  const ranges = [];

  for (let R = 0; R < rows.length; ++R) {
    const outRow = [];
    const row = rows[R];
    const columns = row.querySelectorAll('td, th');

    for (let C = 0; C < columns.length; ++C) {
      const cell = columns[C];
      const colspan = cell.getAttribute('colspan');
      const rowspan = cell.getAttribute('rowspan');
      let cellValue = cell.innerText;

      if (cellValue !== '' && cellValue === +cellValue) {
        cellValue = +cellValue;
      }

      // Skip ranges
      ranges.forEach((range) => {
        if (R >= range.s.r && R <= range.e.r && outRow.length >= range.s.c && outRow.length <= range.e.c) {
          for (let i = 0; i <= range.e.c - range.s.c; ++i) {
            outRow.push(null);
          }
        }
      });

      // Handle Row Span
      if (rowspan || colspan) {
        const rs = rowspan || 1;
        const cs = colspan || 1;
        ranges.push({
          s: { r: R, c: outRow.length },
          e: { r: R + rs - 1, c: outRow.length + cs - 1 },
        });
      }

      // Handle Value
      outRow.push(cellValue !== '' ? cellValue : null);

      // Handle Colspan
      if (colspan) {
        for (let k = 0; k < colspan - 1; ++k) {
          outRow.push(null);
        }
      }
    }
    out.push(outRow);
  }
  return [out, ranges];
}

/**
 * 导出 HTML 表格到 Excel 文件
 * @param {string} id - 表格元素的 ID
 */
export async function exportTableToExcel(id) {
  const theTable = document.getElementById(id);
  const [data, ranges] = generateArray(theTable);

  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet('SheetJS');

  // 添加数据行
  data.forEach((row) => {
    worksheet.addRow(row);
  });

  // 处理合并单元格
  ranges.forEach((range) => {
    // ExcelJS 合并单元格格式: startRow, startColumn, endRow, endColumn (1-based)
    worksheet.mergeCells(
      range.s.r + 1,
      range.s.c + 1,
      range.e.r + 1,
      range.e.c + 1,
    );
  });

  // 生成并下载文件
  const buffer = await workbook.xlsx.writeBuffer();
  saveAs(new Blob([buffer], { type: 'application/octet-stream' }), 'test.xlsx');
}

/**
 * 导出 JSON 数据到 Excel 文件
 * @param {Array} th - 表头数组
 * @param {Array} jsonData - 数据数组（二维数组，每行是一个数组）
 * @param {string} defaultTitle - 文件名（不含扩展名）
 */
export async function exportJsonToExcel(th, jsonData, defaultTitle) {
  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet('SheetJS');

  // 确保 jsonData 是数组
  const rowsData = Array.isArray(jsonData) ? jsonData : [];

  // 添加表头
  if (th && th.length > 0) {
    worksheet.addRow(th);
  }

  // 添加数据行
  rowsData.forEach((row) => {
    if (Array.isArray(row)) {
      worksheet.addRow(row);
    }
  });

  // 计算并设置列宽
  const columnCount = th ? th.length : 0;
  for (let i = 1; i <= columnCount; i++) {
    const column = worksheet.getColumn(i);
    let maxLength = 10;
    column.eachCell({ includeEmpty: false }, (cell) => {
      const cellLength = cell.value ? cell.value.toString().length : 0;
      if (cellLength > maxLength) {
        maxLength = cellLength;
      }
    });
    column.width = Math.min(Math.max(maxLength + 2, 10), 50);
  }

  // 设置表头样式
  if (worksheet.rowCount > 0) {
    const headerRow = worksheet.getRow(1);
    headerRow.font = { bold: true };
    headerRow.fill = {
      type: 'pattern',
      pattern: 'solid',
      fgColor: { argb: 'FFE0E0E0' },
    };
  }

  // 生成并下载文件
  const buffer = await workbook.xlsx.writeBuffer();
  const title = defaultTitle || '列表';
  saveAs(new Blob([buffer], { type: 'application/octet-stream' }), `${title}.xlsx`);
}
