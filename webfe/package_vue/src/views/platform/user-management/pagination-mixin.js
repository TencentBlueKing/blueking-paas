import { paginationFun } from '@/common/utils';

export default {
  data() {
    return {
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      pgSearchValue: '', // 搜索关键字
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

    // 关键字搜索
    pgHandleSearch() {
      const lowerCaseKeyword = this.pgSearchValue.toLocaleLowerCase().trim();
      // 页码重置
      this.pagination.current = 1;

      if (!lowerCaseKeyword) {
        this.pgFilteredData = [...this.pgRawData];
      } else {
        // 使用组件提供的过滤函数
        this.pgFilteredData = this.pgRawData.filter((item) =>
          this.pgFilterFn
            ? this.pgFilterFn(item, lowerCaseKeyword)
            : JSON.stringify(item).toLowerCase().includes(lowerCaseKeyword)
        );
      }
      this.pagination.count = this.pgFilteredData.length;
    },

    // 初始化数据
    pgInitPaginationData(data) {
      this.pgRawData = data;
      this.pgFilteredData = [...data];
      this.pagination.count = data.length;
    },
  },
};
