<template>
  <div class="search-content">
    <section
      v-if="!curSearchKeyword"
      class="search-history-wrapper"
    >
      <section class="search-history" v-if="searchHistory.length">
        <div class="top-wrapper">
          <p class="sub-title">{{ $t('历史搜索') }}</p>
          <div class="clear-history" @click="handleClearHistory">
            <i class="paasng-icon paasng-delete"></i>
            {{ $t('清空历史') }}
          </div>
        </div>
        <span
          class="tag"
          v-for="item in searchHistory"
          :key="item"
          @click="historicalSearch(item)"
        >
          {{ item }}
        </span>
      </section>
      <!-- 推荐搜索 -->
      <section class="recommended-search">
        <p class="sub-title">{{ $t('推荐搜索') }}</p>
        <span
          class="tag"
          v-for="item in recommendedSearch"
          :key="item"
          @click="historicalSearch(item)"
        >
          {{ item }}
        </span>
      </section>
    </section>
    <div v-else v-bkloading="{ isLoading: isLoading, zIndex: 10 }">
      <div class="search-tip-cls" v-dompurify-html="searchTip"></div>
      <!-- 蓝鲸应用 -->
      <section class="app">
        <div class="title-wrapper">
          <div class="total">{{ $t('蓝鲸应用') }}（{{searchData.appList.length}}）</div>
          <div
            v-if="visibleApps.length"
            class="more"
            @click="handleSeeMore('app')">
            {{ $t('查看更多') }}
          </div>
        </div>
        <ul class="app-list-container" v-if="visibleApps.length">
          <li
            class="item"
            v-for="item in visibleApps"
            :key="item.id"
            @click="toAppDetail(item)"
          >
            <img :src="item.logo_url" />
            <div class="app-info">
              <p
                class="code"
                v-bk-overflow-tips="item.code"
                v-dompurify-html="highlight(item.code)"
              ></p>
              <p v-dompurify-html="highlight(item.name)"></p>
            </div>
          </li>
        </ul>
        <p v-else class="empty-tips">{{ $t('没有找到相关结果') }}</p>
      </section>
      <!-- 产品文档 -->
      <section>
        <div class="title-wrapper">
          <div class="total">{{ $t('产品文档') }}（{{searchData.docuList.length + searchData.iwikiList.length}}）</div>
          <div
            v-if="visibleProductDoc.length"
            class="more"
            @click="handleSeeMore('doc')">
            {{ $t('查看更多') }}
          </div>
        </div>
        <ul class="doc-container" v-if="visibleProductDoc.length">
          <li
            class="item"
            v-for="item in visibleProductDoc"
            :key="item.title"
            @click="handleOpen(item)"
          >
            <div
              class="title"
              v-bk-overflow-tips="item.title"
              v-dompurify-html="highlight(item.title)"
            ></div>
            <div class="type">{{ item.source_type === 'iwiki' ? 'iwiki' : $t('资料库') }}</div>
          </li>
        </ul>
        <p v-else class="empty-tips">{{ $t('没有找到相关结果') }}</p>
      </section>
    </div>
  </div>
</template>

<script>
const getDefaultSearchData = () => ({
  appList: [],
  iwikiList: [],
  docuList: [],
});
export default {
  name: 'GlobalSearch',
  props: {
    searchHistory: {
      type: Array,
      default: () => [],
    },
    searchValue: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      searchData: getDefaultSearchData(),
      isLoading: false,
      pageConf: {
        count: 0,
        curPage: 1,
        totalPage: 0,
        limit: 100,
      },
      totalDataCount: 0,
      isSearchHistory: false,
      curSearchKeyword: '',
      recommendedSearch: [
        '开发框架',
        '自定义 Python 版本',
        '安装 apt 包',
        'Celery 开发',
        '数据库慢查询',
        '蓝盾流水线构建云原生应用镜像',
        'bkpaas-cli',
        '内置环境变量',
      ],
    };
  },
  computed: {
    searchTip() {
      return this.$t('已找到 “{k}” 相关的 <i>{n}</i> 条数据', { k: this.curSearchKeyword, n: this.totalDataCount });
    },
    // 应用，最多展示4个
    visibleApps() {
      return this.searchData.appList.slice(0, 4);
    },
    // 产品文档，最多展示20条
    visibleProductDoc() {
      const docs = [...this.searchData.docuList, ...this.searchData.iwikiList];
      return docs;
    },
    isEmptyData() {
      const values = Object.values(this.searchData);
      return values.every(value => Array.isArray(value) && value.length === 0);
    },
  },
  methods: {
    handleSearch() {
      this.fetchData();
    },

    // 全局搜索请求
    async fetchData() {
      this.isLoading = true;
      let allCount = 0;
      try {
        this.curSearchKeyword = this.searchValue;
        const res = await Promise.all([this.fetchApp(), this.fetchIwiki(), this.fetchDocu()].map(item => this.promiseWithError(item)));
        res.forEach((item, index) => {
          const { count, results } = item;
          allCount += count;
          if (index === 0) {
            this.searchData.appList = [...results];
          }
          // 1/2 为产品文档
          if (index === 1) {
            this.searchData.iwikiList = [...results];
          }
          if (index === 2) {
            this.searchData.docuList = [...results];
          }
        });
        this.totalDataCount = allCount;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * @param {Promise} p
     * 处理接口错误时返回的数据问题
     */
    async promiseWithError(p) {
      try {
        const res = await p;
        return {
          count: res.count || 0,
          results: res.results,
        };
      } catch (e) {
        return {
          count: 0,
          results: [],
        };
      }
    },

    fetchApp() {
      return this.$store.dispatch('search/getSearchApp', {
        limit: this.pageConf.limit,
        offset: this.pageConf.limit * (this.pageConf.curPage - 1),
        keyword: this.searchValue,
      });
    },

    fetchDocu() {
      return this.$store.dispatch('search/getSearchDocs', {
        limit: this.pageConf.limit,
        offset: this.pageConf.limit * (this.pageConf.curPage - 1),
        keyword: this.searchValue,
      });
    },

    fetchIwiki() {
      return this.$store.dispatch('search/getSearchIwiki', {
        limit: this.pageConf.limit,
        offset: this.pageConf.limit * (this.pageConf.curPage - 1),
        keyword: this.searchValue,
      });
    },

    highlight(text) {
      const keyword = this.searchValue;
      if (!keyword || !text) return text;
      const escapeRegExp = (str) => {
        return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      };
      const escapedKeyword = escapeRegExp(keyword);
      const regex = new RegExp(`(${escapedKeyword})`, 'gi');
      return text.replace(regex, '<pasmark>$1</pasmark>');
    },

    // 清空搜索历史
    handleClearHistory() {
      this.clearData(false);
      localStorage.removeItem('searchHistory');
      localStorage.setItem('searchHistory', '[]');
      this.$emit('load-history');
    },

    // 查看更多
    handleSeeMore(type) {
      this.$emit('close-search-mode');
      this.clearData();
      this.$router.push({
        name: 'search',
        query: {
          keyword: this.searchValue,
          tab: type === 'app' ? 'app' : 'iwiki',
        },
      });
    },

    // 点击历史记录搜索
    async historicalSearch(text) {
      await this.$emit('change', text);
      this.handleSearch();
    },

    clearData(clearKeyword = true) {
      if (clearKeyword) {
        this.$emit('change', '');
      }
      this.curSearchKeyword = '';
      this.searchData.appList = [];
      this.searchData.iwikiList = [];
      this.searchData.docuList = [];
    },

    // 概览
    toAppSummary(appItem) {
      this.$router.push({
        name: appItem.type === 'cloud_native' ? 'cloudAppSummary' : 'appSummary',
        params: {
          id: appItem.code,
          moduleId: appItem.modules.find(item => item.is_default).name,
        },
      });
    },

    // 详情
    toAppBaseInfo(appItem) {
      this.$router.push({
        name: 'appBaseInfo',
        params: {
          id: appItem.code,
        },
      });
    },

    // 跳转应用详情
    toAppDetail(appItem) {
      this.$emit('close-search-mode');
      this.clearData();
      if (appItem.type === 'engineless_app' || appItem.config_info.engine_enabled) {
        this.toAppSummary(appItem);
        return;
      }
      this.toAppBaseInfo(appItem);
    },

    handleOpen({ url }) {
      window.open(url);
    },
  },
};
</script>

<style lang="scss" scoped>
@mixin flex-center-space {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.search-content {
  padding: 24px;
  .search-tip-cls {
    font-size: 12px;
    line-height: 20px;
    color: #63656E;
    padding-bottom: 16px;
    border-bottom: 1px solid #EAEBF0;
  }
}
.search-history-wrapper {
  .search-history {
    margin-bottom: 24px;
    .top-wrapper {
      @include flex-center-space;
      margin-bottom: 3px;
      font-size: 12px;
      color: #979ba5;
      .clear-history:hover {
        color: #3a84ff;
        cursor: pointer;
      }
    }
  }
  .recommended-search {
    .sub-title {
      font-size: 12px;
      color: #979ba5;
    }
  }
  .tag {
    display: inline-block;
    height: 22px;
    line-height: 22px;
    background: #f0f1f5;
    padding: 0 10px;
    border-radius: 2px;
    margin-right: 8px;
    margin-top: 12px;
    cursor: pointer;
    color: #63656e;

    &:last-child {
      margin-right: 0px;
    }
  }
}
section {
  &.app {
    padding-bottom: 16px;
    border-bottom: 1px solid #EAEBF0;
  }
  .empty-tips {
    text-align: center;
    font-size: 12px;
    color: #979ba5;
  }
  .title-wrapper {
    @include flex-center-space;
    margin: 16px 0 8px;
    font-size: 12px;
    .total {
      color: #979BA5;
    }
    .more {
      color: #3A84FF;
      cursor: pointer;
    }
  }
  .doc-container {
    display: flex;
    flex-wrap: wrap;
    padding: 0;
    margin: 0;
    font-size: 12px;
    .item {
      width: 50%;
      height: 32px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      &:nth-child(odd) {
        padding-right: 18px;
      }
      &:nth-child(even) {
        padding-left: 18px;
      }
      .title {
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        padding-right: 10px;
        color: #313238;
        cursor: pointer;
        &:hover {
          color: #3A84FF;
        }
      }
      .type {
        flex-shrink: 0;
        color: #979ba5;
      }
    }
  }
  .app-list-container {
    display: grid;
    grid-template-columns: repeat(2, 1fr); /* Two equal columns */
    gap: 12px;
    overflow: hidden;
    border-radius: 2px;
    font-size: 12px;
    .item {
      display: flex;
      align-items: center;
      height: 50px;
      background: #f5f7fa;
      padding: 0 16px;
      border-radius: 2px;
      cursor: pointer;
      &:hover {
        background: #F0F1F5;
      }
      img {
        width: 32px;
        height: 32px;
        border-radius: 4px;
      }
      .app-info {
        max-width: 240px;
        margin-left: 8px;
        p {
          color: #979ba5;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .code {
          color: #313238;
          font-size: 14px;
        }
      }
    }
  }
}
</style>

<style lang="scss">
.search-tip-cls i {
  font-weight: 700;
  font-style: normal;
}
section {
  .app-list-container .item .app-info p {
    pasmark {
      color: #FF9C01;
    }
  }
  .doc-container .item .title {
    pasmark {
      color: #FF9C01;
    }
    &:hover pasmark {
      color: #3A84FF;
    }
  }
}
</style>
