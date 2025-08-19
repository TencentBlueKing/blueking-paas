<template lang="html">
  <div>
    <log-filter
      ref="standartLogFilter"
      :key="routeChangeIndex"
      :stream-list="streamList"
      :process-list="processList"
      :log-count="streamLogCount"
      :loading="isStreamLogListLoading"
      :type="'standartLog'"
      :is-use-stream-filter="false"
      @change="handleLogSearch"
      @date-change="handlePickSuccess"
      @reload="handleLogReload"
    />

    <div
      v-if="streamLogFilters.length"
      class="table-filters"
    >
      <ul class="filter-list">
        <li
          v-for="filter of streamLogFilters"
          :key="filter.value"
        >
          <span class="filter-value">实例名: {{ filter.text }}</span>
        </li>
      </ul>
      <span
        v-if="streamLogFilters.length"
        v-bk-tooltips.right="$t('清空筛选条件')"
        class="paasng-icon paasng-close-circle-shape clear-filters-btn"
        @click="handleClearStreamLogFilters"
      />
    </div>

    <div class="ps-log-header">
      <bk-switcher
        v-model="isShowDate"
        :disabled="!streamLogList.length"
        class="bk-small-switcher"
      />
      <span class="text">{{ isShowDate ? $t('隐藏时间') : $t('显示时间') }}</span>
    </div>
    <div
      ref="logContainer"
      v-bkloading="{ isLoading: isStreamLogListLoading && !isScrollLoading }"
      class="ps-log-container"
      :style="{ height: `${contentHeight}px`, overflow: isStreamLogListLoading ? 'hidden' : 'auto' }"
    >
      <div
        v-if="isScrollLoading"
        v-bkloading="{ isLoading: isScrollLoading, color: '#24252c' }"
        class="scroll-loading"
      />
      <p
        v-if="streamLogList.length && !hasNextStreamLog"
        class="no-data"
      >
        {{ $t('已加载该时间段内所有日志') }}
      </p>
      <ul v-if="streamLogList.length">
        <li
          v-for="(log, index) of streamLogList"
          :key="index"
          class="stream-log"
        >
          <span
            v-if="isShowDate"
            class="mr10"
            style="min-width: 160px"
          >
            {{ formatTime(log.timestamp) }}
          </span>
          <!-- <div>
                        <span v-if="log.process_id.length < 5" class="mouseStyle">{{log.process_id}}</span>
                        <span v-else style="cursor: pointer;" v-bk-tooltips.right="{ theme: 'light', content: log.process_id }">{{processIdSlice(log.process_id)}}</span>
                    </div>
                    <template v-if="streamLogFilters.length">
                        <span class="pod-name" style="cursor: default;">{{log.podShortName}}</span>
                    </template>
                    <template v-else>
                        <div class="pod-name" @click="handleAddStreamLogFilters(log)">
                            <span v-bk-tooltips.right="{ theme: 'light', content: $t('仅展示该实例') }">{{log.podShortName}}</span>
                        </div>
                    </template> -->
          <pre
            class="message"
            v-dompurify-html="log.message || '--'"
          />
        </li>
      </ul>
      <div
        v-else
        class="ps-no-result"
      >
        <div
          v-if="!isStreamLogListLoading"
          class="text"
        >
          <empty-dark
            :keyword="emptyDarkConf.keyword"
            @clear-filter="clearFilter"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import moment from 'moment';
import xss from 'xss';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import logFilter from '@/views/dev-center/app/engine/log/comps/log-filter.vue';
import { formatDate } from '@/common/tools';

const xssOptions = {
  whiteList: {
    'bk-highlight-mark': [],
  },
};
const logXss = new xss.FilterXSS(xssOptions);
const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
const initStartDate = moment().subtract(1, 'hours').format('YYYY-MM-DD HH:mm:ss');

export default {
  components: {
    logFilter,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      tabActive: 'standartLog',
      filterKeyword: '',
      contentHeight: 400,
      renderIndex: 0,
      renderFilter: 0,
      routeChangeIndex: 0,
      isLoading: true,
      tableMaxWidth: 700,
      isStreamLogListLoading: true,
      isScrollLoading: false,
      hasNextStreamLog: true,
      isShowDate: true,
      lastScrollId: '',
      initDateTimeRange: [initStartDate, initEndDate],
      lastTopStreamLog: null,
      autoTimer: 0,
      streamLogCount: 0,
      streamLogList: [],
      searchFilterKey: [],
      streamLogFilters: [],
      processList: [],
      streamList: [],
      logParams: {
        start_time: initStartDate,
        end_time: initEndDate,
        environment: '',
        process_id: '',
        stream: '',
        keyword: '',
        levelname: '',
        time_range: '1h',
      },
      isFilter: false,
      formatDate,
      emptyDarkConf: {
        keyword: '',
      },
    };
  },
  watch: {
    'logParams.keyword'(newVal, oldVal) {
      if (newVal === '' && oldVal !== '') {
        if (this.isFilter) {
          this.loadData(false);
          this.isFilter = false;
        }
      }
    },
    '$route.params'(newVal, oldVal) {
      if (newVal.id !== oldVal.id || newVal.moduleId !== oldVal.moduleId) {
        this.isLoading = true;
        this.renderIndex++;
        this.routeChangeIndex++;
        this.resetParams();
        this.loadData();
      }
    },
  },
  beforeRouteLeave(to, from, next) {
    clearInterval(this.autoTimer);
    this.resetParams();
    next(true);
  },
  created() {
    const query = this.$route.query || {};
    this.logParams = {
      start_time: query.start_time || initStartDate,
      end_time: query.end_time || initEndDate,
      environment: query.environment || '',
      process_id: query.process_id || '',
      stream: query.stream || '',
      keyword: query.keyword || '',
      levelname: query.levelname || '',
      time_range: query.time_range || '1h',
    };
  },
  mounted() {
    this.init();
  },
  methods: {
    /**
     * 初始化入口
     */
    init() {
      this.isLoading = true;
      this.loadData();

      const winHeight = window.innerHeight;
      const height = winHeight - 400;
      if (height > 400) {
        this.contentHeight = height;
      }
    },

    handleTabChange(name) {
      this.resetParams();
      this.loadData();
    },

    bindScrollLoading() {
      this.$nextTick(() => {
        if (this.$refs.logContainer) {
          this.$refs.logContainer.addEventListener('scroll', this.scrollLoadStreamLog);
        }
      });
    },

    unbindScrollLoading() {
      this.$refs.logContainer.removeEventListener('scroll', this.scrollLoadStreamLog);
    },

    scrollLoadStreamLog() {
      const { logContainer } = this.$refs;
      const { scrollTop } = logContainer;

      // 滚动到底部
      if (scrollTop === 0) {
        if (this.isScrollLoading) {
          return false;
        }
        this.isScrollLoading = true;

        this.loadData();
      }
    },

    /**
     * 选择自定义时间，并确定
     */
    handlePickSuccess(params) {
      this.logParams = params;
      this.resetStreamLog();
      this.loadData();
    },

    /**
     * 清空查询参数
     */
    removeFilterParams() {
      if (this.$refs.bkSearcher && this.$refs.bkSearcher.removeAllParams) {
        this.$refs.bkSearcher.removeAllParams();
      }
    },

    getParams() {
      return {
        time_range: this.logParams.time_range,
        start_time: this.logParams.start_time,
        end_time: this.logParams.end_time,
      };
    },

    /**
     * 构建过滤参数
     */
    getFilterParams() {
      const params = {
        query: {
          query_string: this.logParams.keyword,
        },
      };

      const filters = this.streamLogFilters;
      filters.forEach((filter) => {
        if (!params.query.terms) {
          params.query.terms = {};
        }
        params.query.terms[filter.key] = [filter.value];
      });

      if (this.logParams.process_id) {
        if (!params.query.terms) {
          params.query.terms = {};
        }
        params.query.terms.process_id = [this.logParams.process_id];
      }

      if (this.logParams.environment) {
        if (!params.query.terms) {
          params.query.terms = {};
        }
        params.query.terms.environment = [this.logParams.environment];
      }

      if (this.logParams.stream) {
        if (!params.query.terms) {
          params.query.terms = {};
        }
        params.query.terms.stream = [this.logParams.stream];
      }
      return params;
    },

    /**
     * 加载所有数据
     */
    loadData(isLoadFilter = true, isMaskLayer) {
      // 限制在一天内
      const startDay = moment(this.logParams.start_time).add(1, 'day');
      const endDay = moment(this.logParams.end_time);
      if (startDay.valueOf() < endDay.valueOf()) {
        this.$bkMessage({
          theme: 'error',
          message: this.$t('请重新选择时间范围，最长不超过一天'),
        });
        return false;
      }
      this.$refs.standartLogFilter.setAutoLoad();
      // 插件标准化输出
      this.getPluginLogList(isMaskLayer);
    },

    /**
     * 清空查询条件
     */
    clearConditionParams() {
      this.logParams.environment = '';
      this.logParams.process_id = '';
      this.logParams.stream = '';
      this.logParams.levelname = '';
    },

    /**
     * 重围搜索参数
     */
    resetParams() {
      this.initDateTimeRange = [initStartDate, initEndDate];
      this.lastScrollId = '';
      this.streamLogList = [];
      this.streamLogFilters = [];
      this.streamList = [];
      this.processList = [];
      this.streamLogCount = 0;
      this.hasNextStreamLog = true;
      this.lastTopStreamLog = null;
      this.isScrollLoading = false;
      this.logParams = {
        start_time: initStartDate,
        end_time: initEndDate,
        environment: '',
        process_id: '',
        stream: '',
        keyword: '',
        time_range: '1h',
        levelname: '',
      };
    },

    /**
     * 关键字高亮
     * @param {String} text 匹配字符串
     */
    setKeywordHight(text) {
      const keywords = this.logParams.keyword.split(';');
      if (keywords.length) {
        keywords.forEach((keyword) => {
          keyword = keyword.trim();
          if (keyword) {
            const tpl = `<span class="ps-keyword-hightlight">${keyword}</span>`;
            const strReg = new RegExp(keyword, 'ig');
            text = text.replace(strReg, tpl);
          }
        });
        return text;
      }
      return text;
    },

    highlight(message) {
      return message.replace(/\[bk-mark\]/g, '<bk-highlight-mark>').replace(/\[\/bk-mark\]/g, '</bk-highlight-mark>');
    },

    // 获取插件标准输出日志数据
    async getPluginLogList(isMaskLayer) {
      const time = this.getParams();
      // 搜索关键字
      const dataBody = this.getFilterParams();
      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
      };
      const pageParams = {
        ...time,
        // offset: 1,
        // limit: 20
      };
      if (isMaskLayer) {
        this.isStreamLogListLoading = true;
      }
      this.unbindScrollLoading();
      this.lastTopStreamLog = document.querySelector('.stream-log');
      try {
        const res = await this.$store.dispatch('plugin/getPluginLogList', { ...params, pageParams, data: dataBody });

        // this.lastScrollId = res.scroll_id;
        // logs: [message 日志内容, timestamp 时间戳]
        const data = res.logs.reverse();
        data.forEach((item) => {
          item.message = this.highlight(logXss.process(item.message));
          // item.podShortName = item.pod_name.split('-').reverse()[0];
        });

        if (!data.length) {
          this.hasNextStreamLog = false;
        } else {
          this.bindScrollLoading();
        }
        this.streamLogCount = res.total;

        if (this.isScrollLoading) {
          this.streamLogList = [...data, ...this.streamLogList];
          setTimeout(() => {
            this.$refs.logContainer.scrollTop = data.length * 35;
          }, 0);
        } else {
          this.streamLogList.splice(0, this.streamLogList.length, ...data);
          setTimeout(() => {
            // 滚动到底部
            this.$refs.logContainer.scrollTop = this.$refs.logContainer.scrollHeight;
          }, 0);
        }
        this.updateEmptyDarkConfig();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isStreamLogListLoading = false;
          this.isScrollLoading = false;
          this.isLoading = false;
        }, 500);
      }
    },

    handleLogSearch(params) {
      this.logParams = params;
      this.resetStreamLog();
      // 改为获取插件日志
      this.loadData(params.isDateChange);

      const query = Object.assign({}, this.$route.query, params);
      this.$router.push({
        name: 'pluginLog',
        params: this.$route.params,
        query,
      });
    },

    handleLogReload(params) {
      this.resetStreamLog();
      this.loadData(false, params);
    },

    resetStreamLog() {
      const { logContainer } = this.$refs;
      this.unbindScrollLoading();
      logContainer.scrollTop = 0;
      this.lastScrollId = '';
      this.lastTopStreamLog = null;
      this.isScrollLoading = false;
      this.hasNextStreamLog = true;
    },

    searchLog(params) {
      this.logParams.environment = '';
      this.logParams.process_id = '';
      this.logParams.stream = '';
      this.logParams.levelname = '';

      params.forEach((item) => {
        const type = item.id;
        const selectItem = item.value;
        this.logParams[type] = selectItem.id;
      });
      this.loadData(false);
    },

    handleAddStreamLogFilters(log) {
      this.streamLogFilters.push({
        key: 'pod_name',
        value: log.pod_name,
        text: log.podShortName,
      });
      this.resetStreamLog();
      this.loadData(false);
    },

    handleClearStreamLogFilters() {
      this.streamLogFilters = [];
      this.renderIndex++;
      this.loadData(false);
    },

    processIdSlice(str) {
      return `${str.slice(0, 4)}.`;
    },

    formatTime(time) {
      return time ? formatDate(time * 1000) : '--';
    },

    clearFilter() {
      this.$refs.standartLogFilter && this.$refs.standartLogFilter.clearKeyword();
      this.isStreamLogListLoading = true;
    },

    updateEmptyDarkConfig() {
      this.emptyDarkConf.keyword = this.logParams.keyword;
    },
  },
};
</script>

<style lang="scss" scoped>
@import '~@/assets/css/mixins/ellipsis.scss';
.result {
  position: relative;
}

.log-filter-box input[type='checkbox'] {
  appearance: none;
}

.logSelectPanel {
  display: inline-block;
  width: 112px;
}

.log-filter-box {
  padding: 15px 0 20px 0;

  .flex {
    display: flex;
  }

  .form-item {
    display: flex;
    .bk-label {
      line-height: 32px;
    }
    .bk-form-content {
      flex: 1;
      position: relative;
    }
  }

  /deep/ .bk-date-picker.long {
    width: 100%;
  }
}

.query-text {
  padding: 0 30px 0 10px;
  width: 304px;
  height: 32px;
  line-height: 32px;
  border-radius: 2px;
  border: solid 1px #c4c6cc;
  font-size: 12px;
  float: left;
  color: #666;
}

.query-date {
  position: relative;
  width: 269px;
  height: 36px;
  float: left;
}

.query-date .query-text {
  width: 227px;
  padding: 0 30px 0 10px;
  cursor: pointer;
  background: url(/static/images/query-date-icon.png) 270px center no-repeat;
  font-size: 13px;
}

.query-date:after {
  content: '';
  position: absolute;
  width: 1px;
  height: 34px;
  background: #ccc;
  top: 1px;
  left: 407px;
}

.chart-box {
  min-height: 150px;
  background: #fafbfd;
}

.result {
  margin: 20px 0;
}

.ps-log-table {
  &:before {
    display: none;
  }
  width: 100%;
  box-sizing: border-box;

  th {
    border-top: none;
    border-right: none;
  }
  td {
    font-size: 12px;
    color: #63656e;
  }
}

.ps-toggle-btn {
  margin-right: 4px;
  cursor: pointer;
  color: #c4c6cc;
  font-size: 12px;
}

.log-message {
  line-height: 20px;
  font-size: 13px;

  pre {
    position: relative;
    max-height: 40px;

    @include multiline-ellipsis;
  }
}

.detail-box {
  padding: 5px 0;
  background-color: #fafbfd;

  li {
    display: flex;
    padding: 0 10px;
    margin-top: 4px;
  }

  .key {
    display: block;
    min-width: 130px;
    line-height: 18px;
    text-align: right;
    padding-right: 10px;
    white-space: nowrap;
    margin-top: -3px;
  }

  .value {
    line-height: 18px;
    display: block;
    flex: 1;
    font-family: 'Helvetica Neue', Helvetica, Tahoma, Arial, 'Microsoft Yahei', 'PingFang SC', STHeiTi, sans-serif;
  }
}

.ps-search-btn {
  margin: 13px 0 0 12px;
  width: 126px;
  line-height: 18px;
  vertical-align: middle;
}

.page-wrapper {
  margin-top: 15px;
  text-align: right;

  .bk-page {
    float: right;
  }
}

.clear-keyword-btn {
  position: absolute;
  right: 10px;
  top: 10px;
  cursor: pointer;
}

.default-time-text {
  position: absolute;
  left: 0;
  top: 0;
  margin: 1px;
  padding: 0 10px;
  width: 290px;
  height: 30px;
  background: #fff;
  z-index: 1;
  box-sizing: border-box;
  line-height: 30px;
  cursor: pointer;
  pointer-events: none;
  font-size: 12px;
}

.time-th {
  width: 200px;
}

.ps-checkbox-default {
  height: 16px;
  margin-top: 8px;
}

.log-main {
  display: flex;
  margin-top: 20px;

  .log-fields {
    width: 210px;
    min-width: 210px;
    background: #f5f6fa;
    border-radius: 2px;
    padding: 15px 10px 15px 20px;

    .title {
      font-size: 14px;
      color: #313238;
      margin-bottom: 18px;
    }

    .field-list {
      max-height: 1200px;
      overflow: auto;
      /deep/ .bk-form-checkbox {
        display: block;
        margin-bottom: 15px;

        & + .bk-form-checkbox {
          margin-left: 0;
        }
      }
    }
  }

  .log-content {
    flex: 1;
    padding-left: 10px;
  }
}
.table-filters {
  margin: 10px 0 0 0;
  display: flex;
  align-items: center;

  .clear-filters-btn {
    cursor: pointer;
  }

  .filter-list {
    > li {
      background: #f0f1f5;
      border-radius: 2px;
      padding: 0 6px 0 6px;
      color: #63656e;
      font-size: 12px;
      display: inline-block;
      margin-right: 10px;

      .filter-value {
        max-width: 300px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        display: inline-block;
        line-height: 26px;
        vertical-align: middle;
      }

      .paasng-icon {
        font-size: 20px;
        vertical-align: middle;
        cursor: pointer;
      }
    }
  }
}

.ps-log-header {
  background: #313238;
  border-bottom: 1px solid #000;
  padding: 10px 20px;
  margin-top: 20px;
  border-radius: 2px 2px 0 0;

  .text {
    margin-left: 5px;
    color: #fff;
    display: inline-block;
    vertical-align: middle;
    font-size: 12px;
  }
}
.ps-log-container {
  background: #313238;
  border-radius: 0 0 2px 2px;
  padding: 20px;
  color: #dcdee5;
  font-size: 12px;
  line-height: 18px;
  overflow: auto;
  min-height: 300px;
  position: relative;

  &::-webkit-scrollbar {
    width: 4px;
    background-color: lighten(transparent, 80%);
  }
  &::-webkit-scrollbar-thumb {
    height: 5px;
    border-radius: 2px;
    background-color: #63656e;
  }

  .ps-no-result {
    width: 80%;
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
  }

  .stream-log {
    display: flex;
    margin-bottom: 8px;
    font-family: Consolas, 'source code pro', 'Bitstream Vera Sans Mono', Consolas, Courier, monospace, '微软雅黑',
      'Arial';

    .pod-name {
      min-width: 95px;
      text-align: right;
      margin-right: 15px;
      color: #979ba5;
      cursor: pointer;

      &:hover {
        color: #3a84ff;
      }
    }
    .message {
      flex: 1;
    }
  }
}
.scroll-loading {
  height: 40px;
  overflow: hidden;
  border-radius: 2px;
  margin-bottom: 10px;
}
.no-data {
  padding: 8px;
  text-align: center;
  background: #1d1e22;
  margin-bottom: 10px;
  border-radius: 2px;
}
.table-wrapper {
  width: auto;
}
.tooltip-icon {
  cursor: pointer;
  vertical-align: middle;
}
.not-found {
  padding: 25px 0 10px 0;
  color: #333;
  font-size: 12px;
}
.mouseStyle {
  cursor: default;
}
</style>
