<template lang="html">
  <div @click="hideAllFilterPopover">
    <log-filter
      ref="customLogFilter"
      :key="routeChangeIndex"
      :stream-list="streamList"
      :process-list="processList"
      :log-count="logsTotal"
      :loading="isChartLoading"
      :type="'customLog'"
      :max-result="pagination.count"
      :is-exceed-max-result-window="isExceedMaxResultWindow"
      @change="handleLogSearch"
      @date-change="handlePickSuccess"
      @reload="handleLogReload"
    />

    <div
      v-if="tableFormatFilters.length"
      class="table-filters"
    >
      <ul class="filter-list">
        <li
          v-for="filter of tableFormatFilters"
          :key="filter.value"
        >
          <span
            v-bk-tooltips="`${filter.key}：${filter.value}`"
            class="filter-value"
          >
            {{ filter.key }}:
            <i>{{ filter.value }}</i>
          </span>
        </li>
      </ul>
      <span
        v-if="tableFilters.length"
        v-bk-tooltips.right="$t('清空筛选条件')"
        class="paasng-icon paasng-close-circle-shape clear-filters-btn"
        @click="handleClearFilters"
      />
    </div>

    <div
      ref="logMain"
      class="log-main"
    >
      <div class="log-fields">
        <p class="title">
          {{ $t('字段设置') }}
          <i
            v-bk-tooltips="$t('仅显示查询结果前200条数据包含的字段，没有出现的字段仍可以通过输入关键字查询')"
            class="paasng-icon paasng-info-circle tooltip-icon"
          />
        </p>
        <template v-if="fieldList.length">
          <bk-checkbox-group
            v-model="fieldSelectedList"
            class="field-list"
          >
            <bk-checkbox
              v-for="field of fieldList"
              :key="field.name"
              class="ps-field-checkbox"
              :value="field.name"
            >
              <span :title="field.name">{{ field.name }}</span>
            </bk-checkbox>
          </bk-checkbox-group>
        </template>
        <template v-else>
          <div
            class="bk-table-empty-block"
            style="margin-top: -40px"
          >
            <table-empty empty />
          </div>
        </template>
      </div>

      <div
        ref="logContent"
        class="log-content"
      >
        <div
          v-bkloading="{ isLoading: isChartLoading }"
          class="chart-box mb20"
          style="width: 100%"
          @click="hideAllFilterPopover"
        >
          <div
            v-charts="chartData"
            style="width: 100%; height: 150px"
          />
          <img
            v-if="!hasChartData"
            class="chart-placeholder"
            src="/static/images/chart-default.svg"
          />
        </div>

        <!-- 查询结果 start -->
        <div
          ref="tableBox"
          v-bkloading="{ isLoading: isLogListLoading }"
          class="table-wrapper log-scroll-cls"
        >
          <table
            id="log-table"
            :key="renderIndex"
            class="ps-table ps-table-default ps-log-table"
          >
            <thead>
              <tr>
                <th
                  style="min-width: 200px"
                  class="time-th"
                >
                  <div class="filter-normal-label">Time</div>
                </th>
                <th>
                  <div class="filter-normal-label">Message</div>
                </th>
                <template v-for="(field, fieldIndex) of fieldSelectedList">
                  <template v-if="fieldOptions[field] && fieldOptions[field].length">
                    <th :key="fieldIndex">
                      <div class="filter-wrapper">
                        <div class="filter-label">
                          <span
                            class="filter-label-text"
                            :title="field"
                          >
                            {{ field }}
                          </span>
                          <div
                            :ref="`filterIcon${field}`"
                            class="paasng-icon paasng-funnel filter-icon"
                            @click.stop.prevent="handleShowFilter($event, field, 'icon')"
                          >
                            <div
                              v-if="fieldPopoverShow[field]"
                              :key="renderFilter"
                              class="filter-popover"
                            >
                              <bk-input
                                v-model="filterKeyword"
                                :placeholder="$t('搜索')"
                                :left-icon="'paasng-icon paasng-search'"
                                :clearable="true"
                              />
                              <template
                                v-if="
                                  !fieldOptions[field].filter(
                                    (option) => option.text.toLowerCase().indexOf(filterKeyword.toLowerCase()) !== -1
                                  ).length
                                "
                              >
                                <div class="not-found">
                                  {{ $t('没找到') }}
                                </div>
                              </template>
                              <bk-checkbox-group
                                :key="JSON.stringify(fieldChecked)"
                                v-model="fieldChecked[field]"
                              >
                                <bk-checkbox
                                  v-for="option of fieldOptions[field]"
                                  v-show="option.text.toLowerCase().indexOf(filterKeyword.toLowerCase()) !== -1"
                                  :key="option.value"
                                  :value="`${field}:${option.value}`"
                                >
                                  <span :title="option.text">{{ option.text }}</span>
                                </bk-checkbox>
                              </bk-checkbox-group>
                              <div class="field-actions">
                                <button
                                  class="confirm"
                                  @click.prevent.stop="handleFilterChange(field)"
                                >
                                  {{ $t('确定') }}
                                </button>
                                <button
                                  class="cancel"
                                  @click.prevent.stop="handleCancelFilterChange(field)"
                                >
                                  {{ $t('取消') }}
                                </button>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </th>
                  </template>
                  <template v-else>
                    <th :key="fieldIndex">
                      {{ field }}
                    </th>
                  </template>
                </template>
              </tr>
            </thead>
            <tbody>
              <template v-if="logList.length">
                <template v-for="(log, index) of logList">
                  <tr
                    :key="index"
                    @click="toggleDetail(log)"
                  >
                    <td class="log-time">
                      <i
                        :class="[
                          'paasng-icon ps-toggle-btn',
                          { 'paasng-right-shape': !log.isToggled, 'paasng-down-shape': log.isToggled },
                        ]"
                      />
                      {{ formatTime(log.timestamp) }}
                    </td>
                    <td class="log-message">
                      <div v-dompurify-html="log.message || '--'" />
                    </td>
                    <template v-for="field of fieldSelectedList">
                      <td
                        :key="field"
                        class="field"
                      >
                        <div v-dompurify-html="log.detail[field] || '--'" />
                      </td>
                    </template>
                  </tr>
                  <tr
                    v-if="log.isToggled"
                    :key="index + 'child'"
                  >
                    <td
                      :colspan="fieldSelectedList.length + 2"
                      style="padding: 0; border-top: none"
                    >
                      <ul class="detail-box">
                        <li
                          v-for="(keyItem, key) of log.detail"
                          :key="key"
                        >
                          <span class="key">{{ key }}：</span>
                          <pre
                            class="value"
                            v-dompurify-html="keyItem || '--'"
                          />
                        </li>
                      </ul>
                    </td>
                  </tr>
                </template>
              </template>
              <template v-else>
                <tr>
                  <td :colspan="fieldSelectedList.length + 2">
                    <div class="ps-no-result">
                      <div class="text">
                        <table-empty
                          :is-content-text="false"
                          :keyword="tableEmptyConf.keyword"
                          :abnormal="tableEmptyConf.isAbnormal"
                          @reacquire="getLogList"
                          @clear-filter="clearFilterKey"
                        />
                        <section class="search-tips">
                          <p style="color: #63656e">
                            {{ $t('您可以按照以下方式优化查询结果：') }}
                          </p>
                          <p
                            v-for="(item, index) in searchLogTips"
                            :key="index"
                          >
                            <span>
                              {{ index + 1 }}.
                              <span>{{ item.text }}</span>
                              <template v-if="item.link">
                                <a
                                  :href="item.url"
                                  target="_blank"
                                >
                                  {{ item.link }}
                                </a>
                              </template>
                            </span>
                          </p>
                        </section>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <!-- 条数过少不展示分页 -->
        <div
          v-if="pagination.count > 9"
          class="ps-page ml0 mr0"
        >
          <bk-pagination
            size="small"
            align="right"
            :current.sync="pagination.current"
            :count="pagination.count"
            :limit="pagination.limit"
            :show-total-count="true"
            @change="handlePageChange"
            @limit-change="handlePageSizeChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import moment from 'moment';
import xss from 'xss';
import appBaseMixin from '@/mixins/app-base-mixin';
import logFilter from './comps/log-filter.vue';
import { throttle } from 'lodash';

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
  mixins: [appBaseMixin],
  data() {
    return {
      name: 'log-component',
      tabActive: 'customLog',
      filterKeyword: '',
      contentHeight: 400,
      renderIndex: 0,
      renderFilter: 0,
      routeChangeIndex: 0,
      isLoading: true,
      lastScrollId: '',
      initDateTimeRange: [initStartDate, initEndDate],
      pagination: {
        current: 1,
        count: 0,
        limit: 20,
      },
      autoTimer: 0,
      fieldChecked: {},
      fieldPopoverShow: {},
      fieldCheckedList: [],
      isChartLoading: false,
      isLogListLoading: false,
      logList: [],
      streamLogList: [],
      searchFilterKey: [],
      tableFilters: [],
      streamLogFilters: [],
      processList: [],
      filterData: [],
      streamList: [],
      fieldList: [],
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
      fieldSelectedList: [],
      isFilter: false,
      searchLogTips: [
        {
          text: this.$t('修改查询时间范围'),
          link: '',
          url: '',
        },
        {
          text: this.$t('优化查询语法'),
          link: this.$t('日志查询语法'),
          url: this.GLOBAL.DOC.LOG_QUERY_SYNTAX,
        },
        {
          text: this.$t('按指引排查'),
          link: this.$t('为什么日志查询为空'),
          url: this.GLOBAL.DOC.LOG_QUERY_EMPTY,
        },
      ],
      tableEmptyConf: {
        isAbnormal: false,
        keyword: '',
      },
      isExceedMaxResultWindow: false,
      logsTotal: 0,
    };
  },
  computed: {
    chartData() {
      const data = this.$store.state.log.chartData;
      return data;
    },
    tableFormatFilters() {
      const results = [];
      const obj = {};
      // 重复key聚合
      this.tableFilters.forEach((item) => {
        if (!obj[item.key]) {
          obj[item.key] = [];
        }
        obj[item.key].push(item.value);
      });
      for (const key in obj) {
        results.push({
          key,
          value: obj[key].join(' | '),
        });
      }
      return results;
    },
    fieldOptions() {
      const options = {};
      const { fieldList } = this;
      fieldList.forEach((field) => {
        options[field.name] = [];
        field.list.forEach((item) => {
          options[field.name].push({
            text: String(item.text),
            value: item.id,
          });
        });
      });
      return options;
    },
    fieldMap() {
      const obj = {};
      const { fieldList } = this;
      fieldList.forEach((field) => {
        obj[field.name] = field.id;
      });
      return obj;
    },
    hasChartData() {
      if (this.chartData.series.length && this.chartData.series[0].data.length) {
        return true;
      }
      return false;
    },
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
        // eslint-disable-next-line no-plusplus
        this.renderIndex++;
        // eslint-disable-next-line no-plusplus
        this.routeChangeIndex++;
        this.resetParams();
        this.loadData();
      }
    },
    fieldSelectedList() {
      const keys = Object.keys(this.fieldChecked);
      this.fieldSelectedList.forEach((item) => {
        if (!this.fieldChecked.hasOwnProperty(item)) {
          this.fieldChecked[item] = [];
          this.fieldPopoverShow[item] = false;
        }
      });
      keys.forEach((item) => {
        if (!this.fieldSelectedList.includes(item)) {
          delete this.fieldChecked[item];
          delete this.fieldPopoverShow[item];
        }
      });
      // eslint-disable-next-line no-plusplus
      this.renderIndex++;
      this.hideAllFilterPopover();
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
      this.getCleaningRules();
      this.loadData();

      const winHeight = document.body?.scrollHeight || window.innerHeight;
      const height = winHeight - 400;
      if (height > 400) {
        this.contentHeight = height;
      }
      this.initTableBox();
      window.addEventListener('resize', throttle(this.initTableBox, 100));
    },

    initTableBox() {
      if (this.$refs.logMain) {
        const width = this.$refs.logMain.getBoundingClientRect()?.width - 220;
        this.$refs.tableBox.style.width = `${width}px`;
        this.$refs.tableBox.style.maxWidth = `${width}px`;
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

    toggleDetail(log) {
      log.isToggled = !log.isToggled;
      const list = JSON.parse(JSON.stringify(this.logList));
      this.logList.splice(0, this.logList.length, ...list);
      this.hideAllFilterPopover();
    },

    getParams() {
      return {
        start_time: this.logParams.start_time,
        end_time: this.logParams.end_time,
        time_range: this.logParams.time_range,
        log_type: 'STRUCTURED',
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

      const filters = this.tabActive === 'customLog' ? this.tableFilters : this.streamLogFilters;
      filters.forEach((filter) => {
        const filterKey = this.fieldMap[filter.key] || filter.key;
        if (!params.query.terms) {
          params.query.terms = {};
        }

        if (!params.query.terms[filterKey]) {
          params.query.terms[filterKey] = [];
        }

        params.query.terms[filterKey].push(filter.value);
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
    loadData(isLoadFilter = true) {
      this.$refs.customLogFilter.setAutoLoad();
      this.pagination.current = 1;
      // 结构化输出
      this.getChartData();
      this.getLogList();
      isLoadFilter && this.getFilterData();
    },

    /**
     * 重围搜索参数
     */
    resetParams() {
      this.initDateTimeRange = [initStartDate, initEndDate];
      this.lastScrollId = '';
      this.tableFilters = [];
      this.fieldSelectedList = [];
      this.fieldList = [];
      this.filterData = [];
      this.streamList = [];
      this.processList = [];
      this.logList = [];
      this.streamLogList = [];
      this.streamLogFilters = [];
      this.pagination = {
        current: 1,
        count: 0,
        limit: 20,
      };
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

    /**
     * 获取图表数据
     */
    async getChartData() {
      const { appCode } = this;
      const moduleId = this.curModuleId;
      const params = this.getParams();
      const filter = this.getFilterParams();

      this.isChartLoading = true;
      try {
        await this.$store.dispatch('log/getChartData', {
          appCode,
          moduleId,
          params,
          filter,
        });
      } catch (res) {
        this.$store.commit('log/updateChartData', {
          series: [],
          timestamps: [],
        });
      } finally {
        setTimeout(() => {
          this.isChartLoading = false;
          this.isLoading = false;
        }, 1000);
      }
    },

    /**
     * 修改页数目回调
     * @param  {Number} pageSize 每页数目
     */
    handlePageSizeChange(pageSize) {
      this.pagination.current = 1;
      this.pagination.limit = pageSize;
      this.$nextTick(() => {
        this.getLogList();
      });
    },

    handlePageChange(page = 1) {
      this.getLogList(page);
    },

    highlight(message) {
      return message.replace(/\[bk-mark\]/g, '<bk-highlight-mark>').replace(/\[\/bk-mark\]/g, '</bk-highlight-mark>');
    },

    /**
     * 获取日志数据
     * @param  {Number} page 第几页数据
     */
    async getLogList(page = 1) {
      const { appCode } = this;
      const moduleId = this.curModuleId;
      const params = this.getParams();
      const pageSize = this.pagination.limit;
      const filter = this.getFilterParams();
      this.isLogListLoading = true;
      try {
        const res = await this.$store.dispatch('log/getLogList', {
          appCode,
          moduleId,
          params,
          page,
          pageSize,
          filter,
        });
        const data = res.logs;
        data.forEach((item) => {
          item.message = this.highlight(logXss.process(item.message));
          if (item.detail) {
            for (const key in item.detail) {
              item.detail[key] = this.highlight(logXss.process(item.detail[key]));
            }
          }
          item.isToggled = false;
        });

        // 是否超过最大范围
        this.isExceedMaxResultWindow = res.total > res.max_result_window;
        this.logsTotal = res.total;
        this.logList.splice(0, this.logList.length, ...data);
        this.pagination.count = this.isExceedMaxResultWindow ? res.max_result_window : res.total;
        this.pagination.current = page;
        this.updateTableEmptyConfig();
        this.tableEmptyConf.isAbnormal = false;
      } catch (res) {
        this.tableEmptyConf.isAbnormal = true;
        this.logList.splice(0, this.logList.length, ...[]);
        this.pagination.count = 0;
      } finally {
        setTimeout(() => {
          this.isLogListLoading = false;
          this.isLoading = false;
        }, 500);
      }
    },

    async getFilterData() {
      const { appCode } = this;
      const moduleId = this.curModuleId;
      const params = this.getParams();

      try {
        const res = await this.$store.dispatch('log/getFilterData', { appCode, moduleId, params });
        const filters = [];
        const fieldList = [];
        const data = res;

        data.forEach((item) => {
          const condition = {
            id: item.key,
            name: item.name,
            text: item.chinese_name || item.name,
            list: [],
          };
          item.options.forEach((option) => {
            condition.list.push({
              id: option[0],
              text: option[0],
            });
          });
          if (condition.name === 'process_id') {
            this.processList = condition.list;
          } else if (condition.name === 'stream') {
            this.streamList = condition.list;
          } else {
            fieldList.push(condition);
          }
          filters.push(condition);
        });
        this.filterData = filters;
        this.fieldList = fieldList;
        this.$refs.customLogFilter && this.$refs.customLogFilter.handleSetParams();
      } catch (res) {
        this.processList = [];
        this.streamList = [];
      }
    },

    handleLogSearch(params) {
      this.logParams = params;
      this.loadData(params.isDateChange);

      const query = Object.assign({}, this.$route.query, params);
      this.$router.push({
        name: 'appLog',
        params: this.$route.params,
        query,
      });
    },

    handleLogReload(params) {
      this.loadData(false);
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

    handleFilterChange(field) {
      const list = [];
      for (const key in this.fieldChecked) {
        this.fieldChecked[key].forEach((field) => {
          const params = field.split(':');
          list.push({
            key: params[0],
            value: params[1],
          });
        });
      }
      this.tableFilters = list;
      this.fieldPopoverShow[field] = false;
      this.loadData(false);
    },

    handleCancelFilterChange(field) {
      this.fieldPopoverShow[field] = false;
      // eslint-disable-next-line no-plusplus
      this.renderIndex++;
    },

    handleRemoveFilter(filter, index) {
      this.tableFilters.splice(index, 1);
    },

    handleClearFilters() {
      this.tableFilters = [];
      // eslint-disable-next-line no-plusplus
      this.renderIndex++;
      // 清空筛选
      for (const key in this.fieldChecked) {
        this.fieldChecked[key] = [];
      }
      this.loadData(false);
    },

    handleExpandRow(row) {
      this.$refs.logList.toggleRowExpansion(row);
    },

    handleShowFilter(e, field) {
      if (!this.fieldPopoverShow[field]) {
        for (const key in this.fieldPopoverShow) {
          this.fieldPopoverShow[key] = false;
        }
        this.fieldPopoverShow[field] = true;
        this.filterKeyword = '';
        // eslint-disable-next-line no-plusplus
        this.renderIndex++;
      } else {
        if (this.$refs[`filterIcon${field}`][0] === e.target) {
          this.handleCancelFilterChange(field);
        }
      }
    },

    hideAllFilterPopover(el) {
      for (const key in this.fieldPopoverShow) {
        this.fieldPopoverShow[key] = false;
      }
      // eslint-disable-next-line no-plusplus
      this.renderFilter++;
    },

    handleHideFilter(field) {
      this.fieldPopoverShow[field] = false;
    },

    clearFilterKey() {
      this.$refs.customLogFilter && this.$refs.customLogFilter.clearKeyword();
    },

    updateTableEmptyConfig() {
      this.tableEmptyConf.keyword = this.logParams.keyword;
    },

    formatTime(time) {
      return time ? moment.unix(time).format('YYYY-MM-DD HH:mm:ss') : '--';
    },

    // 获取清洗规则, 添加对应link
    async getCleaningRules() {
      try {
        const res = await this.$store.dispatch('log/getCleaningRules', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
        });
        this.searchLogTips.push({
          text: this.$t('若自定义日志格式'),
          link: this.$t('检查清洗规则'),
          url: res.clean_url,
        });
      } catch (e) {
        console.error(e);
      }
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

  .chart-placeholder {
    background: #fafbfd;
    position: absolute;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
  }
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

        i {
          font-style: normal;
        }
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
  color: red;
  font-size: 12px;
  line-height: 18px;
  overflow: auto;
  min-height: 300px;
  position: relative;
  margin-bottom: -40px;

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
  overflow: auto;
  .search-tips {
    margin: auto;
    display: flex;
    flex-direction: column;
    line-height: 24px;
    width: fit-content;
    text-align: left;
  }
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
</style>
