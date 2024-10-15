<template>
  <div class="operation-records-container">
    <div class="top-tools">
      <div class="left">
        <div class="title mr20">{{ $t('最近操作记录') }}</div>
        <bk-checkbox v-model="isExecutedByMe" @change="handleChange">
          {{ $t('仅展示我执行的') }}
        </bk-checkbox>
      </div>
      <bk-button
        :text="true"
        title="primary"
        @click="toAppDevelopment"
      >
        {{ $t('更多') }}
      </bk-button>
    </div>
    <div
      class="records card-style"
      :style="{ 'height': `${contentHeight <= defaultMinHeight ? defaultMinHeight : contentHeight}px` }">
      <div class="records-content" v-bkloading="{ isLoading: isLoading, zIndex: 10 }">
        <ul>
          <li
            v-for="item in records"
            :key="item.name"
          >
            <p
              v-bk-overflow-tips
              class="item-title"
            >
              <span
                class="code"
                v-bk-overflow-tips
                @click="toAppOverview(item)"
              >
                {{ item.application.name }}（{{ item.app_code }}）
              </span>
            </p>
            <p
              class="item-content"
              v-bk-overflow-tips
            >
              {{ item.operate }}
            </p>
            <p class="time">
              <i class="paasng-icon paasng-time"></i>
              {{ smartTime(item.at,'fromNow') }}
            </p>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RecentOperationRecords',
  props: {
    contentHeight: {
      type: Number,
      default: 604,
    },
  },
  data() {
    return {
      isExecutedByMe: false,
      isLoading: true,
      records: [],
      defaultMinHeight: 562,
    };
  },
  computed: {
    curUserInfo() {
      return this.$store.state.curUserInfo;
    },
  },
  created() {
    this.getRecentOperationRecords();
  },
  methods: {
    // 获取最近操作记录
    async getRecentOperationRecords() {
      this.isLoading = true;
      const params = {
        limit: 6, // 默认显示7条
        ...(this.isExecutedByMe && { operator: this.curUserInfo.username }),
      };
      try {
        const res = await this.$store.dispatch('baseInfo/getRecentOperationRecords', {
          params,
        });
        this.records = res.results;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },
    handleChange(val) {
      this.getRecentOperationRecords(val);
    },
    // 应用开发页
    toAppDevelopment() {
      this.$router.push({
        name: 'myApplications',
        query: {
          filter: 'at',
        },
      });
    },
    // 概览
    toAppOverview(row) {
      this.$router.push({
        name: row.application.type === 'cloud_native' ? 'cloudAppSummary' : 'appSummary',
        params: { id: row.application.code },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.operation-records-container {
  min-height: 604px;
  padding-top: 6px;
  .top-tools {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    margin-bottom: 14px;
    .left {
      display: flex;
      align-items: flex-end;
    }
    .title {
      font-weight: 700;
      font-size: 16px;
      color: #313238;
    }
  }
  .records {
    padding-left: 24px;
    overflow: hidden;
    background: #ffffff;
  }
  .records-content {
    height: 100%;
    padding-right: 19px;
    overflow-y: auto;
    font-size: 12px;
    color: #63656e;
    .item-title {
      margin-top: 5px;
      line-height: 22px;
      .code {
        font-size: 14px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        cursor: pointer;
        &:hover {
          color: #3A84FF;
        }
      }
    }
    .item-content {
      font-size: 14px;
      line-height: 22px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #979ba5;
    }
    .time {
      margin-top: 4px;
      color: #979BA5;
      i {
        font-size: 16px;
        transform: translateY(0px);
      }
    }
    li {
      padding-bottom: 15px;
      padding-left: 20px;
      position: relative;
      &:first-child {
        margin-top: 20px;
      }
      &::before {
        position: absolute;
        content: '';
        width: 9px;
        height: 9px;
        top: 3px;
        left: 1px;
        border: 2px solid #d8d8d8;
        border-radius: 50%;
      }
      &::after {
        position: absolute;
        content: '';
        width: 1px;
        height: 73px;
        top: 13px;
        left: 5px;
        background: #d8d8d8;
      }
    }
  }
  .records-content::-webkit-scrollbar {
    width: 4px;
    background-color: hsla(0, 0%, 80%, 0);
  }
  .records-content::-webkit-scrollbar-thumb {
    height: 5px;
    border-radius: 2px;
    background-color: #e6e9ea;
  }
  .records-content li:last-child:after {
    background: transparent;
  }
}
</style>
