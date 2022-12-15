<template>
  <div class="ps-log-filter">
    <div
      v-bk-clickoutside="hideDatePicker"
      class="header"
    >
      <div class="fl">
        {{ $t('共') }} <strong>{{ logCount }}</strong> {{ $t('条日志') }}
      </div>
      <div class="reload-action fr">
        <bk-date-picker
          :ref="type"
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
            style="height: 28px;"
            @click="toggleDatePicker"
          >
            <button class="action-btn timer fr">
              <i class="left-icon paasng-icon paasng-clock f16" />
              <span class="text">{{ $t(timerDisplay) }}</span>
              <i class="right-icon paasng-icon paasng-down-shape f12" />
            </button>
          </div>
        </bk-date-picker>

        <button
          v-bk-clickoutside="handleClickOutSide"
          class="action-btn auto"
          style="position: absolute; right: 38px; top: 0;"
          @click="isAutoPanelShow = !isAutoPanelShow"
        >
          <i class="left-icon paasng-icon paasng-tree-application f16" />
          <span class="text">{{ autoTimeConf.label }}</span>
          <i class="right-icon paasng-icon paasng-down-shape f12" />

          <div
            v-if="isAutoPanelShow"
            class="auto-time-list"
          >
            <ul class="wrapper">
              <li
                v-for="time of autoTimeList"
                :key="time.name"
                :class="[{ 'active': autoTimeConf.name === time.name }]"
                @click="handleAuto(time)"
              >
                {{ time.name }}
              </li>
            </ul>
          </div>
        </button>

        <button
          v-bk-tooltips="$t('刷新')"
          class="action-btn refresh"
          style="position: absolute; right: 0; top: 0;"
          @click="handleReload"
        >
          <round-loading v-if="loading" />
          <i
            v-else
            class="left-icon paasng-icon paasng-refresh f16"
            style="color: #979BA5;"
          />
        </button>
      </div>
    </div>
    <div class="filter">
      <!-- <bk-select
                v-model="logParams.environment" :placeholder="$t('环境')"
                style="width: 100px;"
                class="mr10">
                <bk-option v-for="option in envList"
                    :key="option.id"
                    :id="option.id"
                    :name="option.text">
                </bk-option>
            </bk-select>
            <bk-select
                v-model="logParams.stream" :placeholder="$t('输出流')"
                style="width: 100px;"
                class="mr10"
                v-if="isUseStreamFilter">
                <bk-option v-for="option in streamList"
                    :key="option.id"
                    :id="option.id"
                    :name="option.text">
                </bk-option>
            </bk-select>
            <bk-select
                v-model="logParams.process_id" :placeholder="$t('进程')"
                style="width: 100px;"
                class="mr10">
                <bk-option v-for="option in processList"
                    :key="option.id"
                    :id="option.id"
                    :name="option.text">
                </bk-option>
            </bk-select> -->
      <div :class="['log-search-input-wrapper', { 'mr10': isShowExample }]">
        <bk-input
          v-model="keyword"
          :placeholder="$t('请输入过滤关键字，按 Enter 键搜索')"
          :clearable="true"
          :right-icon="'paasng-icon paasng-search'"
          @focus="handleFocus"
          @input="handleInput"
          @keyup.up.native="handleKeyup"
          @keyup.down.native="handleKeydown"
          @keyup.enter.native="handleSearch"
        />
        <div
          v-if="searchHistoryDisplayList.length > 0 && isShowHistoryPanel"
          v-bk-clickoutside="handleClickoutside"
          class="search-history-wrapper"
        >
          <p
            v-for="(item, index) in searchHistoryDisplayList"
            :key="index"
            :class="['history-item', { 'active': curActiveIndex === index }]"
            @click.stop="handleSelectKeyword(item, index)"
          >
            {{ item }}
            <i
              class="paasng-icon paasng-close remove-icon"
              @click.stop="handleRemove(item, index)"
            />
          </p>
        </div>
      </div>
      <bk-dropdown-menu
        v-if="isShowExample"
        ref="dropdown"
        align="right"
        trigger="click"
        @show="dropdownShow"
        @hide="dropdownHide"
      >
        <div
          slot="dropdown-trigger"
          style="padding-left: 19px;"
        >
          <bk-button
            :text="true"
            style="width: 90px; height: 30px; line-height: 30px;"
          >
            {{ isDropdownShow ? $t('隐藏示例') : $t('显示示例') }}
            <i
              :class="['paasng-icon paasng-down-shape f12',{ 'icon-flip': isDropdownShow }]"
              style="top: -1px;"
            />
          </bk-button>
        </div>
        <div
          slot="dropdown-content"
          class="dropdown-content"
          :style="{ width: type === 'customLog' ? '550px' : '400px' }"
        >
          <ul class="examples">
            <li
              v-for="example of logSearchExamples"
              :key="example.key"
            >
              <div class="label">
                {{ example.label }}：
              </div>
              <div
                class="command"
                @click="handleTriggerSearch(example)"
              >
                {{ example.command }}
              </div>
            </li>
          </ul>
          <div class="dropdown-footer">
            {{ $t('更多请参考') }} <a
              :href="GLOBAL.DOC.LOG_QUERY_SYNTAX"
              target="_blank"
            > {{ $t('日志查询语法') }} </a>
          </div>
        </div>
      </bk-dropdown-menu>
    </div>
  </div>
</template>

<script>
    import moment from 'moment';
    import i18n from '@/language/i18n.js';

    const initEndDate = moment().format('YYYY-MM-DD HH:mm:ss');
    const initStartDate = moment().subtract(1, 'hours').format('YYYY-MM-DD HH:mm:ss');
    const dateTextMap = {
        '5m': '最近5分钟',
        '1h': '最近1小时',
        '3h': '最近3小时',
        '12h': '最近12小时',
        '1d': '最近1天',
        '7d': '最近7天'
    };
    let timeRangeCache = '';
    let timeShortCutText = '';

    export default {
        props: {
            logCount: {
                type: Number,
                default: 0
            },
            envList: {
                type: Array,
                default () {
                    return [];
                }
            },
            processList: {
                type: Array,
                default () {
                    return [];
                }
            },
            streamList: {
                type: Array,
                default () {
                    return [];
                }
            },
            loading: {
                type: Boolean,
                default: false
            },
            isUseStreamFilter: {
                type: Boolean,
                default: true
            },
            type: {
                type: String,
                default: ''
            }
        },
        data () {
            const dateShortCut = [
                {
                    text: i18n.t('最近5分钟'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 60 * 1000 * 5);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '5m';
                        timeShortCutText = i18n.t('最近5分钟');
                    }
                },
                {
                    text: i18n.t('最近1小时'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 1);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '1h';
                        timeShortCutText = i18n.t('最近1小时');
                    }
                },
                {
                    text: i18n.t('最近3小时'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 3);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '3h';
                        timeShortCutText = i18n.t('最近3小时');
                    }
                },
                {
                    text: i18n.t('最近12小时'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 12);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '12h';
                        timeShortCutText = i18n.t('最近12小时');
                    }
                },
                {
                    text: i18n.t('最近1天'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 24);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '1d';
                        timeShortCutText = i18n.t('最近1天');
                    }
                }
            ];

            if (this.type === 'customLog' || this.type === 'accessLog') {
                dateShortCut.push({
                    text: i18n.t('最近7天'),
                    value () {
                        const end = new Date();
                        const start = new Date();
                        start.setTime(start.getTime() - 3600 * 1000 * 24 * 7);
                        return [start, end];
                    },
                    onClick (picker) {
                        timeRangeCache = '7d';
                        timeShortCutText = i18n.t('最近7天');
                    }
                });
            }
            return {
                env: 'all',
                stream: 'all',
                timerDisplay: this.$t('最近1小时'),
                pickerRenderIndex: 0,
                isDatePickerOpen: false,
                isDropdownShow: false,
                isAutoPanelShow: false,
                keyword: '',
                autoTimer: 0,
                datePickerOption: {
                    // 小于今天的都不能选
                    disabledDate (date) {
                        return date && date.valueOf() > Date.now() - 86400;
                    }
                },
                autoTimeConf: {
                    label: this.$t('自动刷新'),
                    name: this.$t('关闭自动刷新'),
                    value: 0
                },
                autoTimeList: [
                    {
                        name: this.$t('关闭自动刷新'),
                        label: this.$t('自动刷新'),
                        value: 0
                    },
                    {
                        name: this.$t('5秒'),
                        label: this.$t('5秒 自动刷新'),
                        value: 5 * 1000
                    },
                    {
                        name: this.$t('15秒'),
                        label: this.$t('15秒 自动刷新'),
                        value: 15 * 1000
                    },
                    {
                        name: this.$t('1分钟'),
                        label: this.$t('1分钟 自动刷新'),
                        value: 60 * 1000
                    }
                ],
                dateParams: {
                    start_time: initStartDate,
                    end_time: initEndDate
                },
                logParams: {
                    start_time: initStartDate,
                    end_time: initEndDate,
                    environment: '',
                    process_id: '',
                    stream: '',
                    keyword: '',
                    levelname: '',
                    time_range: '1h'
                },
                initDateTimeRange: [initStartDate, initEndDate],
                logSearchExamples: this.type === 'customLog' ? [
                    {
                        label: this.$t('错误级别的日志'),
                        key: 'json.levelname',
                        command: 'json.levelname:ERROR'
                    },
                    {
                        label: this.$t('精确匹配错误信息'),
                        key: 'json.message',
                        command: 'json.message:"error msg"'
                    },
                    {
                        label: this.$t('多个关键字的匹配'),
                        key: 'response_time',
                        command: 'json.funcName:get_user_info AND json.levelname:ERROR'
                    }
                ] : [
                    {
                        label: this.$t('50X的日志'),
                        key: 'status_code_50X',
                        command: 'status_code:[500 TO 504]'
                    },
                    {
                        label: this.$t('404的日志'),
                        key: 'status_code_404',
                        command: 'status_code:404'
                    },
                    {
                        label: this.$t('响应时间大于500ms的日志'),
                        key: 'response_time',
                        command: 'response_time:>0.5'
                    }
                ],
                dateShortCut: dateShortCut,

                searchHistoryList: [],
                searchHistoryDisplayList: [],
                isShowHistoryPanel: false,
                curActiveIndex: -1
            };
        },
        computed: {
            isShowExample () {
                return ['customLog', 'accessLog'].includes(this.type);
            }
        },
        watch: {
            keyword (newVal, oldVal) {
                if (!newVal && oldVal) {
                    this.handleSearch();
                }
            },
            autoTimeConf: {
                deep: true,
                handler (time) {
                    this.setAutoLoad();
                }
            }
        },
        created () {
            const query = this.$route.query || {};
            this.logParams = {
                start_time: query.start_time || initStartDate,
                end_time: query.end_time || initEndDate,
                environment: query.environment || '',
                process_id: query.process_id || '',
                stream: query.stream || '',
                keyword: query.keyword || '',
                levelname: query.levelname || '',
                time_range: query.time_range || '1h'
            };
            this.keyword = query.keyword || '';
            const dates = [
                this.logParams.start_time || initStartDate,
                this.logParams.end_time || initEndDate
            ];
            if (query.time_range) {
                timeRangeCache = query.time_range;
                timeShortCutText = dateTextMap[timeRangeCache] || '';
            } else if (!query.start_time && !query.end_time) {
                timeRangeCache = '1h';
                timeShortCutText = '最近1小时';
            }
            this.handlerChange(dates);
            this.$watch('logParams', (newDate, oldDate) => {
                if (newDate.start_time !== oldDate.start_time || newDate.start_time !== oldDate.end_time || newDate.time_range !== oldDate.time_range) {
                    // 判断日期是否调整，如果改变需要重新加载filter
                    this.logParams.isDateChange = true;
                } else {
                    this.logParams.isDateChange = false;
                }

                this.$emit('change', this.logParams);
            }, { deep: true });
            console.log('this.logParams', this.logParams);
        },
        methods: {
            handleInput (payload) {
                this.searchHistoryDisplayList = this.searchHistoryList.filter(item => item.indexOf(this.keyword) > -1);
                if (!this.isShowHistoryPanel) {
                    this.isShowHistoryPanel = true;
                }
                this.curActiveIndex = this.searchHistoryDisplayList.findIndex(item => item === this.keyword);
            },

            handleFocus () {
                this.searchHistoryList = JSON.parse(window.localStorage.getItem(`paas-log-search-history-${this.type}`) || '[]').filter(Boolean);
                if (this.searchHistoryDisplayList.length < 1) {
                    this.searchHistoryDisplayList = JSON.parse(JSON.stringify(this.searchHistoryList));
                }
                this.curActiveIndex = this.searchHistoryDisplayList.findIndex(item => item === this.keyword);
                this.isShowHistoryPanel = true;
            },

            handleKeyup () {
                const len = this.searchHistoryList.length;
                this.curActiveIndex--;
                this.curActiveIndex = this.curActiveIndex < 0 ? -1 : this.curActiveIndex;
                if (this.curActiveIndex === -1) {
                    this.curActiveIndex = len - 1;
                }
                this.keyword = this.searchHistoryList[this.curActiveIndex];
            },

            handleKeydown () {
                const len = this.searchHistoryList.length;
                this.curActiveIndex++;
                this.curActiveIndex = this.curActiveIndex > len - 1
                    ? len
                    : this.curActiveIndex;
                if (this.curActiveIndex === len) {
                    this.curActiveIndex = 0;
                }
                this.keyword = this.searchHistoryList[this.curActiveIndex];
            },

            handleRemove (payload, index) {
                this.searchHistoryDisplayList.splice(index, 1);
                const curIndex = this.searchHistoryList.findIndex(item => item === payload);
                this.searchHistoryList.splice(curIndex, 1);
                window.localStorage.setItem(`paas-log-search-history-${this.type}`, JSON.stringify(this.searchHistoryList));
                this.curActiveIndex = -1;
            },

            handleSelectKeyword (payload, index) {
                this.keyword = payload;
                this.logParams.keyword = this.keyword;
                this.curActiveIndex = index;
                this.isShowHistoryPanel = false;
            },

            handleClickoutside () {
                const curDom = Array.from(arguments)[0];
                const className = curDom.target.className;
                if (className.indexOf('bk-form-input') > -1) {
                    this.isShowHistoryPanel = true;
                    return;
                }
                this.isShowHistoryPanel = false;
                this.curActiveIndex = -1;
            },

            toggleDatePicker () {
                this.isDatePickerOpen = !this.isDatePickerOpen;
            },

            handleSearch () {
                // 只存储最近10条记录
                const MAX_LEN = 10;
                if (!this.searchHistoryList.includes(this.keyword)) {
                    if (this.searchHistoryList.length === MAX_LEN) {
                        this.searchHistoryList.shift();
                    }
                    this.searchHistoryList.push(this.keyword);
                    window.localStorage.setItem(`paas-log-search-history-${this.type}`, JSON.stringify(this.searchHistoryList));
                }
                this.logParams.keyword = this.keyword;
                this.isShowHistoryPanel = false;
            },

            dropdownShow () {
                this.isDropdownShow = true;
            },

            dropdownHide () {
                this.isDropdownShow = false;
            },

            handleTriggerSearch (example) {
                this.keyword = example.command;
                this.logParams.keyword = example.command;
            },

            clearTimer () {
                this.clearInterval(this.autoTimer);
            },

            /**
             * 选择自定义时间
             */
            handlerChange (dates, type) {
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
                this.pickerRenderIndex++;
            },

            /**
             * 选择自定义时间，并确定
             */
            handlerPickSuccess () {
                this.isDatePickerOpen = false;

                setTimeout(() => {
                    this.logParams = Object.assign(this.logParams, {
                        start_time: this.dateParams.start_time,
                        end_time: this.dateParams.end_time,
                        levelname: '',
                        time_range: this.dateParams.time_range
                    });
                }, 200);
            },

            handleSetParams () {
                // const isExistEnv = this.envList.some(item => item.id === this.logParams.environment)
                // const isExistStream = this.streamList.some(item => item.id === this.logParams.stream)
                // const isExistProcess = this.processList.some(item => item.id === this.logParams.process_id)
                // if (!isExistEnv) this.logParams.environment = ''
                // if (!isExistStream) this.logParams.stream = ''
                // if (!isExistProcess) this.logParams.process_id = ''
            },

            /**
             * 清空查询条件
             */
            clearConditionParams () {
                this.logParams.environment = '';
                this.logParams.process_id = '';
                this.logParams.stream = '';
                this.logParams.levelname = '';
            },

            hideDatePicker () {
                if (['standartLog', 'customLog', 'accessLog'].includes(this.type)) {
                    this.isDatePickerOpen = false;
                }
            },

            setAutoLoad () {
                clearInterval(this.autoTimer);
                if (this.autoTimeConf.value) {
                    this.autoTimer = setInterval(() => {
                        this.$emit('reload', false);
                    }, this.autoTimeConf.value);
                }
            },

            handleReload () {
                if (this.loading) {
                    return false;
                }
                this.setAutoLoad();
                this.$emit('reload', true);
            },

            handleAuto (conf) {
                this.autoTimeConf = conf;
            },

            handleClickOutSide () {
                this.isAutoPanelShow = false;
            }
        }
    };
</script>

<style lang="scss" scoped>
    @import '~@/assets/css/mixins/clearfix.scss';
    .ps-log-filter {
        .header {
            @include clearfix;
            line-height: 28px;
            margin-bottom: 7px;
        }

        .reload-action {
            padding-right: 195px;
            position: relative;

            .action-btn {
                margin-left: 10px;
            }
        }

        .auto-time-list {
            width: 100%;
            position: absolute;
            left: 0;
            top: 30px;
            z-index: 1000;

            .wrapper {
                background: #FFF;
                text-align: left;
                font-size: 12px;
                border: 1px solid #dcdee5;
                border-radius: 2px;
                box-shadow: 0px 2px 6px 0px rgba(0,0,0,0.1);
                margin-top: 5px;

                li {
                    line-height: 32px;
                    padding: 0 10px;

                    &:hover {
                        background: #EAF3FF;
                        color: #3A84FF;
                    }

                    &.active {
                        background: #F4F6FA;
                        color: #3A84FF;
                    }
                }
            }
        }

        .action-btn {
            height: 28px;
            background: #F5F6FA;
            line-height: 28px;
            min-width: 28px;
            display: flex;
            border-radius: 2px;
            cursor: pointer;
            position: relative;

            .text {
                min-width: 90px;
                line-height: 28px;
                text-align: left;
                color: #63656E;
                font-size: 12px;
                display: inline-block;
            }

            .left-icon,
            .right-icon {
                width: 28px;
                height: 28px;
                line-height: 28px;
                color: #C4C6CC;
                display: inline-block;
                text-align: center;
            }

            &.refresh {
                width: 28px;
            }
        }

        .filter {
            display: flex;
            align-items: center;
        }

        /deep/ .bk-date-picker.long {
            width: auto;
        }

        .log-search-input-wrapper {
            position: relative;
            flex: 1 1 0%;
            .search-history-wrapper {
                position: absolute;
                top: 33px;
                padding: 8px 0;
                width: 100%;
                background-color: #fff;
                border: 1px solid #e5e5e5;
                border-radius: 3px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
                z-index: 1999;
                .history-item {
                    position: relative;
                    padding: 0 15px;
                    line-height: 28px;
                    font-size: 12px;
                    color: #2e2e2e;
                    cursor: pointer;
                    &.active {
                        background-color: #eee;
                        .remove-icon {
                            display: block;
                        }
                    }
                    &:hover {
                        background-color: #eee;
                        .remove-icon {
                            display: block;
                        }
                    }
                    .remove-icon {
                        display: none;
                        position: absolute;
                        top: 9px;
                        right: 15px;
                        font-weight: 600;
                        font-size: 12px;
                        transform: scale(.8);
                        cursor: pointer;
                    }
                }
            }
        }
    }
    .dropdown-trigger-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid #c4c6cc;
        height: 32px;
        min-width: 68px;
        border-radius: 2px;
        padding: 0 15px;
        color: #63656E;
    }
    .dropdown-trigger-btn.paasng-icon {
        font-size: 18px;
    }
    .dropdown-trigger-btn .paasng-icon {
        font-size: 22px;
    }
    .dropdown-trigger-btn:hover {
        cursor: pointer;
        border-color: #979ba5;
    }
    .dropdown-content {
        margin-top: 10px;
    }
    .examples {
        padding: 0 24px;
        margin-bottom: 15px;
        li {
            display: flex;
            font-size: 14px;
            line-height: 20px;
            margin-bottom: 5px;

            .label {
                color: #63656E;
                white-space: nowrap;
            }
            .command {
                color: #3A84FF;
                padding-left: 2px;
                cursor: pointer;
            }
        }
    }
    .dropdown-footer {
        padding: 0 24px;
        text-align: right;
        margin-bottom: 10px;
    }
    .example-strong {
        font-weight: normal;
        background: #eee;
        padding: 0 3px;
        margin: 0 2px;
        border-radius: 2px;
        color: #333;
    }
</style>
