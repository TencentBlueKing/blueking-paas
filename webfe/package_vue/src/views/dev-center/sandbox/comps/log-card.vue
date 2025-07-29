<template>
  <div :class="['log-card', { collapsed: isCollapsed }]">
    <div class="top">
      <div class="title">
        <i
          class="paasng-icon paasng-right-shape"
          @click="isCollapsed = !isCollapsed"
        ></i>
        {{ title }}
      </div>
      <div class="tools">
        <bk-select
          v-if="!isBuildLog"
          :disabled="false"
          v-model="curRunLogType"
          style="width: 120px"
          :clearable="false"
          ext-cls="select-custom"
          @change="handleLogTypeSwitch"
        >
          <bk-option
            v-for="option in logTypeList"
            :key="option.name"
            :id="option.name"
            :name="option.name"
          ></bk-option>
        </bk-select>
        <template v-if="!isBuildLog">
          <bk-dropdown-menu
            @show="dropdownShow"
            @hide="dropdownHide"
            trigger="click"
            ref="dropdown"
          >
            <div
              class="dropdown-trigger-btn"
              slot="dropdown-trigger"
            >
              <span>{{ curRefreshTime }}</span>
              <i :class="['bk-icon icon-angle-down', { 'icon-flip': isDropdownShow }]"></i>
            </div>
            <ul
              class="bk-dropdown-list"
              slot="dropdown-content"
            >
              <li
                v-for="item in refreshTimeList"
                :key="item"
              >
                <a
                  href="javascript:;"
                  @click="handleTrigger(item)"
                >
                  {{ item }}
                </a>
              </li>
            </ul>
          </bk-dropdown-menu>
          <span class="line"></span>
        </template>
        <i
          class="paasng-icon paasng-refresh"
          @click="handleRefresh"
        ></i>
      </div>
    </div>
    <div
      ref="logRef"
      :class="['logs-box', { loading: loading, empty: !displayLogs }]"
      v-bkloading="{ isLoading: loading, opacity: 1, color: '#313238', zIndex: 10 }"
    >
      <template v-if="displayLogs">
        <template v-if="Array.isArray(displayLogs)">
          <pre
            v-for="(item, index) in displayLogs"
            :key="index"
            class="log log-item"
            v-dompurify-html="item"
          />
        </template>
        <pre
          v-else
          class="log log-item"
          v-dompurify-html="loading ? '' : displayLogs"
        />
      </template>
      <table-empty
        v-else
        empty
        :empty-title="$t('暂无日志')"
      />
    </div>
  </div>
</template>

<script>
export default {
  name: 'LogCard',
  props: {
    title: {
      type: String,
      default: '',
    },
    logs: {
      type: [String, Object],
      required: true,
    },
    loading: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      refreshTimeList: ['off', '5s', '10s', '30s'],
      isDropdownShow: false,
      curRefreshTime: '5s',
      curRunLogType: '',
      isCollapsed: false,
      ansiUp: null,
    };
  },
  computed: {
    type() {
      return this.title === this.$t('构建日志') ? 'build' : 'run';
    },
    isBuildLog() {
      return this.type === 'build';
    },
    displayLogs() {
      let curLogs = this.isBuildLog ? this.logs ?? '' : this.logs[this.curRunLogType] ?? '';
      // 如果 curLogs 是一个数组，每项之间添加换行符
      if (Array.isArray(curLogs)) {
        curLogs = curLogs.join('\n');
      }
      return this.ansiUp ? this.ansiUp.ansi_to_html(curLogs) : curLogs;
    },
    logTypeList() {
      if (!this.isBuildLog && this.logs !== null) {
        return Object.keys(this.logs).map((v) => {
          return { name: v };
        });
      }
      return [];
    },
  },
  watch: {
    displayLogs: {
      handler() {
        this.scrollBottom();
      },
      deep: true,
    },
    loading(newVal) {
      if (!newVal) {
        this.scrollBottom();
      }
    },
    logTypeList(newVal, oldVal) {
      if (newVal.length || oldVal.length) {
        const oldName = oldVal[0]?.name;
        const newName = newVal[0]?.name;
        if (this.curRunLogType) {
          this.curRunLogType = this.curRunLogType === oldName ? newName : this.curRunLogType;
        } else {
          this.curRunLogType = newName;
        }
      }
    },
  },
  created() {
    const AU = require('ansi_up');
    this.ansiUp = new AU.default();
  },
  methods: {
    dropdownShow() {
      this.isDropdownShow = true;
    },
    dropdownHide() {
      this.isDropdownShow = false;
    },
    handleTrigger(data) {
      this.curRefreshTime = data;
      bus.$emit('change-refresh-time', {
        key: this.type,
        value: data === 'off' ? 'off' : data.slice(0, -1),
      });
      this.$refs.dropdown.hide();
    },
    handleRefresh() {
      bus.$emit('refresh-log', this.type);
    },
    // 滚动底部
    scrollBottom() {
      this.$nextTick(() => {
        const el = this.$refs.logRef;
        if (el) {
          el.scrollTo({
            top: el.scrollHeight || 0, // 滚动到底部
            behavior: 'smooth', // 平滑滚动
          });
        }
      });
    },
    handleLogTypeSwitch() {
      this.scrollBottom();
    },
  },
};
</script>

<style lang="scss" scoped>
.log-card {
  display: flex;
  flex-direction: column;
  transition: flex 0.2s ease;
  overflow: hidden;
  &.collapsed {
    flex: 0 0 50px;
    .top .paasng-right-shape {
      transform: rotate(0deg);
    }
    .logs-box {
      display: none !important;
    }
  }
  .top {
    height: 32px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
    color: #c4c6cc;
    .paasng-right-shape {
      cursor: pointer;
      transform: rotate(90deg);
    }
    .tools {
      display: flex;
      align-items: center;
      .dropdown-trigger-btn {
        cursor: pointer;
        .bk-icon {
          margin-left: 4px;
          display: inline-block;
          color: #63656e;
          font-size: 18px;
        }
      }
      .icon-flip {
        transform: rotate(180deg);
      }
      .line {
        display: inline-block;
        margin: 0 13px;
        width: 1px;
        height: 14px;
        background: #63656e;
      }
      .paasng-refresh {
        cursor: pointer;
      }
      .select-custom {
        margin-right: 10px;
        color: #c4c6cc;
      }
    }
  }
  .logs-box {
    flex: 1;
    display: block;
    overflow-y: auto;
    font-size: 12px;
    color: #dcdee5;
    padding: 8px 12px;
    background: #2a2b2f;
    .log {
      font-size: 12px;
      color: #dcdee5;
      letter-spacing: 0;
      line-height: 20px;
    }
    &.loading {
      overflow: hidden;
    }
    &.empty {
      display: flex;
      align-items: center;
      justify-content: center;
    }
    &::-webkit-scrollbar {
      width: 4px;
      background-color: lighten(transparent, 80%);
    }
    &::-webkit-scrollbar-thumb {
      height: 5px;
      border-radius: 2px;
      background-color: #616161;
    }
  }
}
</style>
