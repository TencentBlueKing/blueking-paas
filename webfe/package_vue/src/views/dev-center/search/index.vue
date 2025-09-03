<template>
  <div
    class="paas-search-wrapper mt30"
    :style="{ 'min-height': `${minHeight}px` }"
  >
    <h4 class="title">
      {{ $t('搜索') }}
    </h4>
    <section class="search-hearder">
      <bk-input
        v-model="value"
        clearable
        :placeholder="$t('输入搜索内容')"
        style="width: 766px;"
        ext-cls="paas-search-input"
        @enter="handleSearch"
      />
      <bk-button
        theme="primary"
        icon="search"
        ext-cls="paas-search-button"
        size="large"
        @click="handleSearch"
      >
        {{ $t('搜索') }}
      </bk-button>
    </section>
    <paas-content-loader
      class="content-wrapper"
      :is-loading="isLoading"
      placeholder="search-loading"
      :height="450"
    >
      <bk-tab
        v-show="isShowTab"
        ref="tabRef"
        :active.sync="curTab"
        type="unborder-card"
        ext-cls="paas-search-tab-cls"
        @tab-change="handleSwitchTab"
      >
        <bk-tab-panel
          v-for="(panel, index) in panels"
          :key="index"
          v-bind="panel"
        >
          <template slot="label">
            <span class="panel-name">{{ panel.label }}</span>
            <i :class="['panel-count', { active: panel.name === curTab }]">{{ panel.count }}</i>
          </template>
        </bk-tab-panel>
      </bk-tab>
      <div
        v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
        class="table-content"
      >
        <template v-if="isEmpty">
          <section class="empty-wrapper">
            <table-empty empty />
          </section>
        </template>
        <template v-else>
          <app
            v-if="curTab === 'app'"
            :data="searchData[curTab].list"
          />
          <docu
            v-if="curTab === 'docu'"
            :data="searchData[curTab].list"
            :filter-key="filterKey"
          />
          <iwiki
            v-if="curTab === 'iwiki'"
            :data="searchData[curTab].list"
            :filter-key="filterKey"
          />
        </template>
      </div>
      <div
        v-if="isShowPageConf"
        :class="['mb20 mt20', { 'set-padding': isSetPadding }]"
      >
        <bk-pagination
          size="small"
          align="right"
          :current.sync="pageConf.curPage"
          :count="pageConf.count"
          :limit="pageConf.limit"
          :limit-list="pageConf.limitList"
          @change="pageChange"
          @limit-change="handlePageSizeChange"
        />
      </div>
    </paas-content-loader>
  </div>
</template>
<script>
// import merge from 'webpack-merge';
import { bus } from '@/common/bus';
import App from './comps/application';
import Docu from './comps/docu';
import Iwiki from './comps/iwiki';

const getDefaultSearchData = () => ({
  app: {
    list: [],
  },
  iwiki: {
    list: [],
  },
  docu: {
    list: [],
  },
});

export default {
  name: '',
  components: {
    App,
    Docu,
    Iwiki,
  },
  data() {
    return {
      minHeight: 550,
      value: '',
      searchData: getDefaultSearchData(),
      curTab: 'app',
      pageConf: {
        count: 0,
        curPage: 1,
        totalPage: 0,
        limit: 10,
        limitList: [5, 10, 20, 50],
      },
      isLoading: false,
      tableLoading: false,
      isShowTab: true,
      panels: [
        { name: 'app', label: this.$t('应用'), count: 0 },
        { name: 'iwiki', label: 'iwiki', count: 0 },
        { name: 'docu', label: this.$t('资料库'), count: 0 },
      ],
      filterKey: '',
    };
  },
  computed: {
    isEmpty() {
      const curTabData = this.panels.find(item => item.name === this.curTab);
      return curTabData.count < 1 && !this.isLoading && this.isShowTab;
    },
    isShowPageConf() {
      const curTabData = this.panels.find(item => item.name === this.curTab);
      return curTabData.count > 0;
    },
    isSetPadding() {
      return ['docu', 'iwiki'].includes(this.curTab);
    },
  },
  created() {
    bus.$emit('on-being-search');
    this.value = this.$route.query.keyword || '';
    this.filterKey = this.value;
    this.fetchData();
  },
  mounted() {
    const HEADER_HEIGHT = 50;
    const FOOTER_HEIGHT = 70;
    const winHeight = window.innerHeight;
    const contentHeight = winHeight - HEADER_HEIGHT - FOOTER_HEIGHT;
    if (contentHeight > this.minHeight) {
      this.minHeight = contentHeight;
    }
  },
  methods: {
    handleSearch() {
      if (this.isLoading) {
        return;
      }
      this.handleResetData();
      if (this.value === '') {
        this.isShowTab = false;
        this.filterKey = '';
        return;
      }
      this.fetchData();
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

    async fetchData() {
      this.isLoading = true;
      try {
        const res = await Promise.all([this.fetchApp(), this.fetchIwiki(), this.fetchDocu()].map(item => this.promiseWithError(item)));
        res.forEach((item, index) => {
          const { count, results } = item;
          this.panels[index].count = count || 0;
          if (index === 0) {
            this.searchData.app.list = [...results];
          }
          if (index === 1) {
            this.searchData.iwiki.list = [...results];
          }
          if (index === 2) {
            this.searchData.docu.list = [...results];
          }
        });
        this.filterKey = this.value;
        this.isShowTab = true;
        this.$nextTick(() => {
          this.$refs.tabRef && this.$refs.tabRef.$refs.tabLabel && this.$refs.tabRef.$refs.tabLabel.forEach(label => label.$forceUpdate());
        });

        this.handleInitTab();
        this.handleInitPageConf();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.isLoading = false;
        this.$router.push({
          query: Object.assign(this.$route.query, { keyword: this.filterKey }),
        });
      }
    },

    handleInitTab() {
      const queryTab = this.$route.query.tab;
      this.curTab = queryTab || 'app';
    },

    handleResetData() {
      this.searchData = getDefaultSearchData();
      this.pageConf = Object.assign(this.pageConf, {
        count: 0,
        curPage: 1,
        totalPage: 0,
        limit: 10,
      });
      this.panels.forEach((item) => {
        item.count = 0;
      });
      this.curTab = 'app';

      if (!this.isShowTab) {
        return;
      }

      this.$nextTick(() => {
        this.$refs.tabRef && this.$refs.tabRef.$refs.tabLabel && this.$refs.tabRef.$refs.tabLabel.forEach(label => label.$forceUpdate());
      });
    },

    handleInitPageConf() {
      const curData = this.panels.find(item => item.name === this.curTab);
      this.pageConf.count = curData.count;
      this.pageConf.curPage = 1;
      this.pageConf.limit = 10;
      this.pageConf.totalPage = Math.ceil(curData.count / this.pageConf.limit);
    },

    fetchApp() {
      return this.$store.dispatch('search/getSearchApp', {
        limit: this.pageConf.limit,
        offset: this.pageConf.limit * (this.pageConf.curPage - 1),
        keyword: this.value,
      });
    },

    fetchDocu() {
      return this.$store.dispatch('search/getSearchDocs', {
        limit: this.pageConf.limit,
        offset: this.pageConf.limit * (this.pageConf.curPage - 1),
        keyword: this.value,
      });
    },

    fetchIwiki() {
      return this.$store.dispatch('search/getSearchIwiki', {
        limit: this.pageConf.limit,
        offset: this.pageConf.limit * (this.pageConf.curPage - 1),
        keyword: this.value,
      });
    },

    handleSwitchTab() {
      this.handleInitPageConf();
      this.$nextTick(() => {
        this.$refs.tabRef && this.$refs.tabRef.$refs.tabLabel && this.$refs.tabRef.$refs.tabLabel.forEach(label => label.$forceUpdate());
      });

      this.$router.push({
        query: Object.assign(this.$route.query, { tab: this.curTab }),
      });
    },

    async pageChange(page) {
      this.pageConf.curPage = page;
      this.tableLoading = true;
      try {
        if (this.curTab === 'app') {
          const res = await this.fetchApp();
          this.searchData.app.list = [...res.results];
        } else if (this.curTab === 'docu') {
          const res = await this.fetchDocu();
          this.searchData.docu.list = [...res.results];
        } else {
          const res = await this.fetchIwiki();
          this.searchData.iwiki.list = [...res.results];
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.tableLoading = false;
      }
    },

    async handlePageSizeChange(pageSize) {
      this.pageConf.limit = pageSize;
      this.tableLoading = true;
      try {
        if (this.curTab === 'app') {
          const res = await this.fetchApp();
          this.searchData.app.list = [...res.results];
        } else if (this.curTab === 'docu') {
          const res = await this.fetchDocu();
          this.searchData.docu.list = [...res.results];
        } else {
          const res = await this.fetchIwiki();
          this.searchData.iwiki.list = [...res.results];
        }
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.tableLoading = false;
      }
    },
  },
};
</script>
<style lang="scss">
    .paas-search-wrapper {
        width: 1180px;
        margin: 0 auto;
        .title {
            font-size: 18px;
            color: #313238;
        }
        .search-hearder {
            margin-top: 20px;
            display: flex;
            justify-content: flex-start;
        }
        .paas-search-input {
            .bk-form-input {
                height: 38px;
                font-size: 16px;
                border-radius: 2px 0 0 2px;
            }
        }

        .paas-search-button {
            margin-left: -1px;
            border-radius: 0 2px 2px 0;
            .bk-icon.left-icon {
                margin-right: 5px !important;
                font-size: 22px !important;
            }
        }

        .content-wrapper {
            margin-top: 10px;
            .paas-search-tab-cls {
                .bk-tab-section {
                    display: none;
                }
            }
            .panel-icon,
            .panel-name,
            .panel-count {
                display: inline-block;
                vertical-align: middle;
                margin: 0 3px;
            }
            .panel-count {
                min-width: 16px;
                height: 16px;
                padding: 0 4px ;
                line-height: 16px;
                border-radius: 8px;
                text-align: center;
                font-style: normal;
                font-size: 12px;
                color: #fff;
                background-color: #c4c6cc;
                &.active {
                    background-color: #3a84ff;
                }
            }
            .table-content {
                position: relative;
                min-height: 200px;
                .empty-wrapper {
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    i {
                        font-size: 65px;
                        color: #c3cdd7;
                    }
                    .text {
                        font-size: 12px;
                        color: #63656e;
                        text-align: center;
                    }
                }
            }
        }

        .set-padding {
            padding-right: 320px;
        }
    }
</style>
