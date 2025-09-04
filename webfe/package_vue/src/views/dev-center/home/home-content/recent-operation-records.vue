<template>
  <div class="operation-records-container">
    <div class="top-tools">
      <div class="left">
        <div class="title mr20">{{ $t('最近操作记录') }}</div>
        <bk-checkbox
          ext-cls="checkbox-custom-cls"
          v-model="isExecutedByMe"
          @change="handleChange"
        >
          {{ $t('仅展示我执行的') }}
        </bk-checkbox>
      </div>
    </div>
    <div
      class="records card-style"
      :style="{ height: `${contentHeight <= defaultMinHeight ? defaultMinHeight : contentHeight}px` }"
    >
      <div
        class="records-content"
        v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
      >
        <ul>
          <li
            v-for="item in records"
            :key="item.name"
          >
            <div
              class="record-item"
              @click="toAppOverview(item)"
            >
              <p
                v-bk-overflow-tips
                class="item-title"
              >
                <span
                  class="code"
                  v-bk-overflow-tips
                >
                  {{ item.application.name }}（{{ item.app_code }}）
                </span>
              </p>
              <p
                class="item-content"
                v-bk-overflow-tips
              >
                <span v-if="isMultiTenantDisplayMode">
                  <bk-user-display-name :user-id="item.operator"></bk-user-display-name>
                  {{ formattedOperate(item.operate) }}
                </span>
                <template v-else>{{ item.operate }}</template>
              </p>
              <p class="time">
                <i class="paasng-icon paasng-time"></i>
                {{ smartTime(item.at, 'fromNow') }}
              </p>
            </div>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
import { mapState, mapGetters } from 'vuex';

// 操作记录筛选的 localStorage 键名
const SHOW_ONLY_MY_OPERATIONS_PREFERENCE = 'show_only_my_operations_preference';
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
      isExecutedByMe: this.loadLocalStorageBoolean(SHOW_ONLY_MY_OPERATIONS_PREFERENCE, false),
      isLoading: true,
      records: [],
      defaultMinHeight: 562,
    };
  },
  computed: {
    ...mapState(['curUserInfo']),
    ...mapGetters(['isMultiTenantDisplayMode']),
  },
  created() {
    this.getRecentOperationRecords();
  },
  methods: {
    // 获取最近操作记录
    async getRecentOperationRecords() {
      this.isLoading = true;
      const params = {
        limit: 5,
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
      window.localStorage.setItem(SHOW_ONLY_MY_OPERATIONS_PREFERENCE, val);
    },
    // 概览
    toAppOverview(row) {
      this.$router.push({
        name: row.application.type === 'cloud_native' ? 'cloudAppSummary' : 'appSummary',
        params: { id: row.application.code },
      });
    },
    formattedOperate(operate) {
      return operate ? operate.split(' ').slice(1).join(' ') : '';
    },
    loadLocalStorageBoolean(key, defaultValue) {
      const value = window.localStorage.getItem(key);
      return value === null ? defaultValue : value === 'true';
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
      .checkbox-custom-cls /deep/ .bk-checkbox::after {
        height: 10px !important;
        width: 6px !important;
      }
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
    .record-item {
      padding: 0 0 5px 6px;
    }
    .record-item:hover {
      cursor: pointer;
      background: #fafbfd;
      border-radius: 2px;
      .code {
        color: #3a84ff;
      }
    }
    .item-title {
      margin-top: 5px;
      line-height: 22px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      .code {
        font-size: 14px;
        cursor: pointer;
      }
    }
    .item-content {
      font-size: 12px;
      line-height: 22px;
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      overflow: hidden;
      text-overflow: ellipsis;
      color: #979ba5;
    }
    .time {
      margin-top: 4px;
      color: #979ba5;
      i {
        font-size: 16px;
        transform: translateY(0px);
      }
    }
    li {
      padding-bottom: 15px;
      padding-left: 14px;
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
        height: calc(100% - 6px);
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
