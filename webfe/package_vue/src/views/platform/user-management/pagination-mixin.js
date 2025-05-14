import { paginationFun } from '@/common/utils';

export default {
  data() {
    return {
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
        limitList: [5, 10, 15, 20],
      },
      pgSearchValue: '', // 搜索关键字
      pgFieldFilter: {
        filterField: null,
        filterValue: null,
      }, // 字段过滤
      pgFilteredData: [], // 过滤数据
      pgRawData: [], // 原始接口数据
    };
  },
  computed: {
    // 分页数据
    pgPaginatedData() {
      const { pageData } = paginationFun(this.pgFilteredData, this.pagination.current, this.pagination.limit);
      return pageData;
    },
  },
  methods: {
    // 页容量改变
    pgHandlePageLimitChange(limit) {
      // 页容量变化，页码重置
      this.pagination.current = 1;
      this.pagination.limit = limit;
    },

    // 页面改变
    pgHandlePageChange(page) {
      this.pagination.current = page;
    },

    // 关键字搜索、字段筛选
    pgHandleCombinedSearch() {
      const keyword = this.pgSearchValue.trim();
      const { filterField, filterValue } = this.pgFieldFilter;

      // 页码重置
      this.pagination.current = 1;

      // 如果没有搜索条件和筛选条件，显示所有数据
      if (!keyword && (!filterField || !filterValue)) {
        this.pgFilteredData = [...this.pgRawData];
        this.pagination.count = this.pgFilteredData.length;
        return;
      }

      // 同时应用关键字搜索和字段筛选
      this.pgFilteredData = this.pgRawData.filter((item) => {
        // 1. 关键字搜索条件
        const keywordMatch = !keyword || (
          this.pgFilterFn ? this.pgFilterFn(item, keyword) : JSON.stringify(item).includes(keyword)
        );
        // 2. 字段筛选条件
        const fieldMatch = !filterField || !filterValue || this.checkFieldMatch(item[filterField], filterValue);
        return keywordMatch && fieldMatch;
      });

      this.pagination.count = this.pgFilteredData.length;
    },

    // 辅助方法：检查字段匹配（精确字符串匹配）
    checkFieldMatch(fieldValue, filterValue) {
      if (fieldValue === undefined || fieldValue === null) {
        return false;
      }
      // 转为字符串进行精确匹配
      return String(fieldValue) === String(filterValue);
    },

    // 初始化数据
    pgInitPaginationData(data) {
      this.pgRawData = data;
      this.pgFilteredData = [...data];
      this.pagination.count = data.length;
    },
  },
};
