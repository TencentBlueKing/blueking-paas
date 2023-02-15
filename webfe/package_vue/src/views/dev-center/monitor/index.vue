<template lang="html">
  <div
    class="bk-apps-wrapper mt30"
    :style="{ 'min-height': `${minHeight}px` }"
  >
    <div class="wrap">
      <div class="paas-application-tit">
        <h2> {{ $t('我的告警') }} </h2>

        <div class="fright">
          <div
            v-bk-clickoutside="hideDatePicker"
            :class="['data-search', { 'reset-left': curDateType !== 'custom' }]"
          >
            <bk-date-picker
              v-model="initDateTimeRange"
              :shortcuts="dateShortCut"
              :shortcuts-type="'relative'"
              :format="'yyyy-MM-dd HH:mm:ss'"
              :placement="'bottom-end'"
              :placeholder="$t('选择日期时间范围')"
              :shortcut-close="true"
              :type="'datetimerange'"
              :options="datePickerOption"
              :open="isDatePickerOpen"
              @change="handlerChange"
              @pick-success="handlerPickSuccess"
            >
              <div
                slot="trigger"
                style="width: 310px;"
                @click="toggleDatePicker"
              >
                <button class="action-btn timer">
                  <i class="left-icon paasng-icon paasng-clock f16" />
                  <span class="text">{{ timerDisplay }}</span>
                  <i class="right-icon paasng-icon paasng-down-shape f12" />
                </button>
              </div>
            </bk-date-picker>
          </div>
          <div class="paas-search">
            <bk-input
              v-model="filterKey"
              :placeholder="$t('输入应用名称、ID，按Enter搜索')"
              :clearable="true"
              :right-icon="'paasng-icon paasng-search'"
              @enter="searchApp"
            />
          </div>
        </div>
      </div>

      <div
        v-bkloading="{ isLoading: isLoading, opacity: 0 }"
        :class="['apps-table-wrapper', { 'min-h': isLoading }, { 'reset-min-h': !isLoading && !curPageData.length }]"
      >
        <template v-if="curPageData.length">
          <div
            v-for="(appItem, appIndex) in curPageData"
            :key="appIndex"
            class="table-item"
            :class="{ 'mt': appIndex !== curPageData.length - 1 }"
          >
            <div class="item-header">
              <div
                class="basic-info"
                @click="toPage(appItem)"
              >
                <img
                  :src="appItem.logo_url ? appItem.logo_url : defaultImg"
                  class="app-logo"
                >
                <span class="app-name">
                  {{ appItem.app_name }}
                </span>
              </div>
              <div
                class="module-info"
                @click="expandedPanel(appItem)"
              >
                <template>
                  <span class="module-name">
                    {{ $t('告警次数') }}&nbsp;({{ appItem.count || 0 }})
                    <i
                      class="paasng-icon unfold-icon expanded-icon"
                      :class="appItem.expanded ? 'paasng-angle-up' : 'paasng-angle-down'"
                    />
                  </span>
                </template>
              </div>
              <div class="visit-operate">
                <div class="app-operation-section">
                  <bk-button
                    theme="primary"
                    text
                    style="margin-left: 80px;"
                    @click="toMonitorRecord(appItem)"
                  >
                    {{ $t('更多') }}
                    <i class="paasng-icon paasng-external-link" />
                  </bk-button>
                </div>
              </div>
            </div>
            <div
              v-if="appItem.expanded"
              class="item-content"
            >
              <div
                v-bkloading="{ isLoading: appItem.tableLoading, opacity: 1 }"
                class="apps-table-wrapper paas-monitor-table"
              >
                <bk-table
                  v-if="!appItem.tableLoading"
                  :data="appItem.alarmList"
                  size="small"
                  ext-cls="alarm-list-table"
                  :outer-border="false"
                  :header-border="false"
                >
                  <bk-table-column
                    :label="$t('告警模块')"
                    width="180"
                  >
                    <template slot-scope="{ row }">
                      <span>{{ row.module }}</span>
                    </template>
                  </bk-table-column>
                  <bk-table-column
                    :label="$t('告警环境')"
                    width="90"
                  >
                    <template slot-scope="{ row }">
                      <span>{{ row.env === 'prod' ? $t('生产环境') : $t('预发布环境') }}</span>
                    </template>
                  </bk-table-column>
                  <bk-table-column
                    :label="$t('告警类型')"
                    width="200"
                  >
                    <template slot-scope="{ row }">
                      <span v-bk-tooltips="row.genre.name">{{ row.genre.name || '--' }}</span>
                    </template>
                  </bk-table-column>
                  <bk-table-column
                    :label="$t('告警次数')"
                    prop="count"
                    width="80"
                  />
                  <bk-table-column
                    :label="$t('最近一次告警开始时间')"
                    prop="start"
                    width="150"
                  />
                  <bk-table-column :label="$t('最近一次告警内容')">
                    <template slot-scope="{ row }">
                      <span v-bk-tooltips="row.message">{{ row.message || '--' }}</span>
                    </template>
                  </bk-table-column>
                </bk-table>
              </div>
            </div>
          </div>
        </template>
        <template v-if="!isLoading && !curPageData.length">
          <div class="ps-no-result">
            <table-empty empty />
          </div>
        </template>
      </div>

      <div
        v-if="pageConf.count"
        style="margin: 20px 0;"
      >
        <bk-pagination
          size="small"
          align="right"
          :current.sync="pageConf.current"
          :count="pageConf.count"
          :limit="pageConf.limit"
          @change="pageChange"
          @limit-change="handlePageSizeChange"
        />
      </div>
    </div>
  </div>
</template>

<script>
    import moment from 'moment';

    const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
    const initStartDate = moment().subtract(1, 'days').format('YYYY-MM-DD HH:mm:ss');

    let timeRangeCache = '';
    let timeShortCutText = '';
    export default {
        name: '',
        data () {
            const dateShortCut = [
                {
                    text: this.$t('最近5分钟'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 60 * 1000 * 5);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '5m';
                        timeShortCutText = this.$t('最近5分钟');
                    }
                },
                {
                    text: this.$t('最近1小时'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 1);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '1h';
                        timeShortCutText = this.$t('最近1小时');
                    }
                },
                {
                    text: this.$t('最近3小时'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 3);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '3h';
                        timeShortCutText = this.$t('最近3小时');
                    }
                },
                {
                    text: this.$t('最近12小时'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 12);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '12h';
                        timeShortCutText = this.$t('最近12小时');
                    }
                },
                {
                    text: this.$t('最近1天'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 24);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '1d';
                        timeShortCutText = this.$t('最近1天');
                    }
                },
                {
                    text: this.$t('最近7天'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '7d';
                        timeShortCutText = this.$t('最近7天');
                    }
                }
            ];
            return {
                isLoading: true,
                minHeight: 550,
                dataList: [],
                curPageData: [],
                curSearchData: [],
                appNum: '',
                defaultImg: '/static/images/default_logo.png',
                // 搜索词
                filterKey: '',
                pageConf: {
                    count: 0,
                    current: 0,
                    limit: 10
                },
                isFilter: false,

                datePickerOption: {
                    // 小于今天的都不能选
                    disabledDate (date) {
                        return date && date.valueOf() > Date.now() - 86400;
                    }
                },
                dateShortCut: dateShortCut,
                initDateTimeRange: [initStartDate, initEndDate],
                dateParams: {
                    start_time: initStartDate,
                    end_time: initEndDate
                },
                timerDisplay: this.$t('最近1天'),
                isDatePickerOpen: false,
                curDateType: 'custom'
            };
        },
        watch: {
            filterKey (newVal, oldVal) {
                if (newVal === '' && oldVal !== '') {
                    if (this.isFilter) {
                        this.curSearchData = [];
                        this.fetchMonitorList();
                        this.isFilter = false;
                    }
                }
            }
        },
        created () {
            this.fetchMonitorList();
        },
        mounted () {
            const HEADER_HEIGHT = 50;
            const FOOTER_HEIGHT = 70;
            const winHeight = window.innerHeight;
            const contentHeight = winHeight - HEADER_HEIGHT - FOOTER_HEIGHT;
            if (contentHeight > this.minHeight) {
                this.minHeight = contentHeight;
            }
        },
        methods: {
            /**
             * 选择自定义时间
             */
            handlerChange (dates, type) {
                this.curDateType = !type ? 'custom' : type;
                this.dateParams.start_time = dates[0];
                this.dateParams.end_time = dates[1];
                this.dateParams.time_range = timeRangeCache || 'customized';
                if (timeShortCutText) {
                    this.timerDisplay = timeShortCutText;
                } else {
                    this.timerDisplay = `${dates[0]} - ${dates[1]}`;
                }
                timeShortCutText = ''; // 清空
                timeRangeCache = ''; // 清空
            },

            toggleDatePicker () {
                this.isDatePickerOpen = !this.isDatePickerOpen;
            },

            hideDatePicker () {
                this.isDatePickerOpen = false;
            },

            /**
             * 选择自定义时间，并确定
             */
            handlerPickSuccess () {
                this.isDatePickerOpen = false;
                setTimeout(() => {
                    this.fetchMonitorList();
                }, 300);
            },

            toPage (appItem) {
                this.$router.push({
                    name: 'appSummary',
                    params: {
                        id: appItem.app_code
                    }
                });
            },

            initPageConf () {
                this.pageConf.current = 1;
                const total = this.dataList.length;
                this.pageConf.count = total;
            },

            pageChange (page = 1) {
                this.pageConf.current = page;
                const data = this.getDataByPage(page);
                this.curPageData.splice(0, this.curPageData.length, ...data);
            },

            handlePageSizeChange (pageSize) {
                this.pageConf.limit = pageSize;
                this.pageConf.current = 1;
                this.pageChange(this.pageConf.current);
            },

            /**
             * 获取当前这一页的数据
             *
             * @param {number} page 当前页
             *
             * @return {Array} 当前页数据
             */
            getDataByPage (page) {
                if (!page) {
                    this.pageConf.current = page = 1;
                }
                let startIndex = (page - 1) * this.pageConf.limit;
                let endIndex = page * this.pageConf.limit;
                if (startIndex < 0) {
                    startIndex = 0;
                }
                if (endIndex > this.dataList.length) {
                    endIndex = this.dataList.length;
                }
                return this.dataList.slice(startIndex, endIndex);
            },

            toMonitorRecord (item) {
                this.$router.push({
                    name: 'monitorAlarm',
                    params: {
                        id: item.app_code
                    }
                });
            },

            expandedPanel (item) {
                const uuidArr = [];
                item.record_ids.forEach(recordItem => {
                    uuidArr.push(recordItem);
                });
                const searchkey = {
                    ordering: '-start',
                    uuid: uuidArr
                };
                const params = {
                    code: item.app_code,
                    search: searchkey
                };
                item.expanded = !item.expanded;
                this.fetchAlarmList(item, params);
            },

            async fetchAlarmList (payload, params = {}) {
                payload.tableLoading = true;
                try {
                    const res = await this.$store.dispatch('alarm/getPersonalAlarmList', params);
                    const listMap = {}
                    ;(res.results || []).forEach(item => {
                        const key = `${item.module}${item.env}${item.genre.uuid}`;
                        if (!listMap[key]) {
                            this.$set(listMap, key, {});
                            listMap[key].count = 1;
                            listMap[key].list = [item];
                        } else {
                            ++listMap[key].count;
                            listMap[key].list.push(item);
                        }
                    });
                    const tempList = [];
                    for (const key in listMap) {
                        const item = listMap[key].list[0];
                        this.$set(item, 'count', listMap[key].count);
                        tempList.push(item);
                    }
                    payload.alarmList.splice(0, payload.alarmList.length, ...tempList);
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                } finally {
                    payload.tableLoading = false;
                }
            },

            searchApp () {
                if (this.filterKey === '') {
                    return;
                }
                this.isFilter = true;
                const filterList = this.dataList.filter(item => item.app_name.indexOf(this.filterKey) !== -1 || item.app_code.indexOf(this.filterKey) !== -1);
                this.curSearchData.splice(0, this.curSearchData.length, ...filterList);
                this.pageConf.current = 1;
                const total = filterList.length;
                this.pageConf.count = total;
                let page = this.pageConf.current;
                if (!page) {
                    this.pageConf.current = page = 1;
                }
                let startIndex = (page - 1) * this.pageConf.limit;
                let endIndex = page * this.pageConf.limit;
                if (startIndex < 0) {
                    startIndex = 0;
                }
                if (endIndex > this.curSearchData.length) {
                    endIndex = this.curSearchData.length;
                }

                this.curPageData = this.curSearchData.slice(startIndex, endIndex);
            },

            async fetchMonitorList (page = 1) {
                const params = {
                    start_after: this.dateParams.start_time,
                    start_before: this.dateParams.end_time
                };
                this.isLoading = true;
                try {
                    const res = await this.$store.dispatch('alarm/getPersonalMonitor', params)
                    ;(res.results || []).forEach(item => {
                        item.expanded = false;
                        item.alarmList = [];
                        item.tableLoading = false;
                    });
                    this.dataList.splice(0, this.dataList.length, ...(res.results || []));
                    this.initPageConf();
                    this.curPageData = this.getDataByPage(this.pageConf.current);
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || this.$t('接口异常')
                    });
                } finally {
                    this.isLoading = false;
                }
            }
        }
    };
</script>

<style lang="scss" scoped>
    .bk-apps-wrapper {
        width: 100%;
        padding: 28px 0 44px;
    }

    .data-search {
        display: inline-block;
        position: relative;
        top: 3px;
        left: 183px;
        &.reset-left {
            left: 40px;
        }
    }

    .paas-search {
        display: inline-block;
    }

    .action-btn {
        height: 32px;
        background: #F5F6FA;
        line-height: 32px;
        min-width: 28px;
        display: flex;
        border-radius: 2px;
        cursor: pointer;
        position: relative;

        .text {
            min-width: 90px;
            line-height: 32px;
            text-align: left;
            color: #63656E;
            font-size: 12px;
            display: inline-block;
        }

        .left-icon,
        .right-icon {
            width: 28px;
            height: 28px;
            line-height: 32px;
            color: #C4C6CC;
            display: inline-block;
            text-align: center;
        }

        &.refresh {
            width: 28px;
        }
    }

    .apps-table-wrapper {
        position: relative;
        width: 100%;
        min-height: 100px;
        &.min-h {
            min-height: 255px;
        }
        &.reset-min-h {
            min-height: 400px;
        }
        .table-item {
            width: calc(100% - 2px);
            background: #fff;
            border-radius: 2px;
            border: 1px solid #dcdee5;
            &.mt {
                margin-bottom: 10px;
            }
            &:hover {
                box-shadow: 0px 3px 6px 0px rgba(99, 101, 110, .1);
            }
        }
        .ps-no-result {
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
        }
        .item-header {
            width: 100%;
            height: 64px;
            line-height: 64px;
            .basic-info {
                display: inline-block;
                position: relative;
                width: 30%;
                height: 100%;
                cursor: pointer;
                &:hover {
                    .app-name {
                        color: #3a84ff;
                    }
                }
                .app-name {
                    display: inline-block;
                    position: relative;
                    top: -2px;
                    height: 100%;
                    padding-left: 6px;
                    max-width: 250px;
                    text-overflow: ellipsis;
                    overflow: hidden;
                    white-space: nowrap;
                    color: #63656e;
                    font-size: 14px;
                    font-weight: bold;
                    vertical-align: middle;
                    &:hover {
                        color: #3a84ff;
                    }
                }
                .app-logo {
                    position: relative;
                    top: 10px;
                    margin: 0 5px 0 12px;
                    width: 32px;
                    height: 32px;
                    border-radius: 4px;
                    // cursor: pointer;
                    &:hover {
                        color: #3a84ff;
                    }
                    &.reset-ml {
                        margin-left: 48px;
                    }
                }
            }
            .module-info {
                display: inline-block;
                width: 50%;
                cursor: pointer;
                &:hover {
                    .expanded-icon {
                        display: inline-block;
                    }
                }
                .module-name {
                    display: inline-block;
                    margin: 0 4px;
                    min-width: 100px;
                    color: #ff4d4d;
                }
                .expanded-icon {
                    display: none;
                    color: #3a84ff;
                }
            }
            .visit-operate {
                display: inline-block;
            }
        }
        .item-content {
            .header-shadow {
                width: 100%;
                height: 5px;
                background: linear-gradient(180deg,rgba(99,101,110,1) 0%,rgba(99,101,110,0) 100%);
                opacity: .05;
            }
            .apps-table-wrapper {
                padding: 0 30px !important;
            }
        }
    }

    .migrate {
        position: absolute;
        right: 532px;
    }

    .app-operation-section {
        position: relative;
        button {
            i {
                position: relative;
                top: 1px;
                font-size: 20px;
            }
        }
    }

    .shaixuan,
    .shaixuan input {
        cursor: pointer;
    }

    .create-app {
        position: absolute;
        right: 427px;
    }

    .paas-operation-icon {
        color: #fff;
        font-size: 14px;
        height: 36px;
        line-height: 36px;
        border-radius: 18px;
        width: 120px;
        text-align: center;
        margin-left: 19px;
        background: #3A84FF;
        transition: all .5s;

        &:hover {
            background: #4b9cf2;
        }

        .paasng-icon {
            margin-right: 5px;
        }
    }

    .ps-table-app {
        color: #666;

        &:hover {
            color: #3a84ff;
        }
    }

    .ps-table-operate {
        color: #3a84ff;
        padding: 0 9px;

        &:hover {
            color: #699df4;
        }
    }

    .ps-table th.pl30,
    .ps-table td.pl30 {
        padding-left: 30px;
    }

    .ps-table tr:hover {
        .ps-table-app {
            color: #3a84ff;
        }
    }

    div.choose-panel {
        input {
            appearance: none;
        }
    }

    .table-applications {

        th,
        td {
            font-size: 14px;
        }
    }

    .table-applications {
        width: 100%;
    }

    label {
        display: inline;
        cursor: pointer;
    }

    .button-holder {
        display: block;
        line-height: 30px;
    }

    .paas-application-tit {
        padding: 20px 0;
        color: #666;
        line-height: 36px;
        position: relative;
    }

    .paas-application-tit h2 {
        font-size: 18px;
        font-weight: normal;
        display: inline-block;
        color: #313238;
    }

    .paas-application-tit h2 span {
        color: #666;
    }

    .disabledBox .section-button {
        color: #d7eadf;
        cursor: not-allowed;
    }

    .disabledBox .section-button:hover {
        color: #d7eadf;
    }

    .disabledBox .section-button img {
        opacity: .3;
    }

    .paas-legacy-app {
        position: absolute;
        right: 482px;
    }

    .paas-search {
        width: 320px;
    }

    .choose-box {
        position: absolute;
        right: -2px;
        margin-top: 3px;
        width: 92px;
        overflow: hidden;
        height: 30px;
        border: solid 1px #afbec5;
        padding: 0;
        line-height: 30px;
    }

    .choose {
        color: #666;
        font-size: 14px;
        height: 30px;
        line-height: 30px;
        width: 52px;
        padding-left: 14px;
    }

    .application-choose-btn {
        border-top: solid 1px #e9edee;
        text-align: center;
        padding: 6px 0;
    }

    .application-choose-btn a {
        width: 68px;
        height: 30px;
        line-height: 30px;
        border: solid 1px #e9edee;
        margin: 8px 5px;
        border-radius: 2px;
        color: #666;
        transition: all .5s;
    }

    .application-choose-btn a:hover {
        background: #e9edee;
    }

    .application-choose-btn a.active {
        background: #3A84FF;
        border: solid 1px #3A84FF;
        color: #fff;
    }

    .application-choose-btn a.active:hover {
        background: #3a84ff;
    }

    .application-choose img {
        position: relative;
        top: 2px;
        padding-right: 8px;
    }

    .application-list {
        overflow: hidden;
        margin: 57px -25px 31px -25px;
    }

    .application-list li {
        float: left;
        width: 360px;
        padding: 0 25px;
        text-align: center;
        color: #333;
        padding-bottom: 5px;
    }

    .application-list li h2 {
        width: 100%;
        height: 64px;
        overflow: hidden;
        font-weight: normal;
    }

    .application-list li h2 a {
        color: #333;
        font-size: 18px;
        line-height: 64px;
    }

    .application-list-text {
        height: 48px;
        overflow: hidden;
    }

    .application-list-text a {
        color: #3A84FF;
        padding: 0 4px;
    }

    .application-list li img {
        width: 360px;
        height: 180px;
        float: left;
        margin-top: 24px;
        box-shadow: 0 3px 5px #e5e5e5;
        transition: all .5s;
    }

    .application-list li:hover img {
        transform: translateY(-4px);
    }

    .application-blank {
        background: #fff;
        padding: 50px 30px;
        text-align: center;
        color: #666;
        box-shadow: 0 2px 5px #e5e5e5;
        margin-top: 2px;
    }

    .application-blank h2 {
        font-size: 18px;
        color: #333;
        line-height: 42px;
        padding: 14px 0;
        font-weight: normal;
    }

    .application-blank .paas-operation-icon {
        width: 140px;
        margin: 34px auto 30px;
    }

    .choose-panel {
        position: absolute;
        right: 0;
        top: 60px;
        width: 228px;
        border-top: solid 1px #e9edee;
        box-shadow: 0 2px 5px #e5e5e5;
        background: #fff;
        height: auto;
        overflow: hidden;
        padding: 5px 0 0 0;
        z-index: 99;
        transition: all .5s;
    }

    .save {
        width: 20px;
        height: 24px;
        vertical-align: middle;
        background: url(/static/images/save-icon.png) center center no-repeat;
    }

    .save.on,
    .save:hover {
        background: url(/static/images/save-icon2.png) center center no-repeat;
    }

    .save:hover {
        opacity: 0.4
    }

    .save.on:hover {
        opacity: .65;
    }

    .overflow {
        overflow: hidden;
        padding: 0 20px;
    }

    .paasng-angle-up,
    .paasng-angle-down {
        padding-left: 3px;
        transition: all .5s;
        font-size: 12px;
        font-weight: bold;
        color: #5bd18b;
    }

    .open .section-button .paasng-angle-down {
        position: absolute;
        top: 8px;
        right: 12px;
    }

    .ps-btn-visit-disabled .paasng-angle-down,
    .ps-btn-visit:disabled .paasng-angle-down,
    .ps-btn-visit[disabled] .paasng-angle-down {
        color: #d7eadf !important;
    }
    .wrap {
        width: 1180px;
    }
</style>
