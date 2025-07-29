<template>
  <bk-dialog
    v-model="dialogVisible"
    theme="primary"
    :width="480"
    :mask-close="false"
    :show-footer="false"
    @value-change="valueChange"
    @after-leave="dialogAfterLeave"
    ext-cls="del-cluster-dialog-cls"
  >
    <div class="dialog-title">
      <div class="icon-wrapper">
        <i class="bk-icon bk-dialog-mark bk-dialog-warning icon-exclamation"></i>
      </div>
      <p class="mt20">{{ $t('无法删除集群') }}</p>
    </div>
    <div class="dialog-delete-info">
      <p>{{ $t('集群（{n}）正在被以下租户、应用使用，无法删除', { n: clusterName }) }}：</p>
      <div class="del-alert-info-content">
        <div
          v-dompurify-html="deletePromptOne"
          v-if="config.allocated_tenant_ids?.length"
        ></div>
        <div
          v-dompurify-html="deletePromptTwo"
          v-if="displayBoundApps.length"
        ></div>
      </div>
    </div>
    <ul
      class="bound-apps mt15"
      v-if="displayBoundApps.length"
    >
      <i
        v-bk-tooltips="$t('复制')"
        class="paasng-icon paasng-general-copy"
        v-copy="JSON.stringify(config.bound_app_module_envs, null, 2)"
      ></i>
      <li class="list-title app-item">
        <div class="column app-id">{{ $t('应用 ID') }}</div>
        <div class="column module">{{ $t('模块') }}</div>
        <div class="column env">{{ $t('环境') }}</div>
      </li>
      <li
        v-for="(item, index) in displayBoundApps"
        class="app-item"
        :key="index"
      >
        <div
          class="column app-id"
          v-bk-overflow-tips
        >
          {{ item.app_code }}
        </div>
        <div
          class="column module"
          v-bk-overflow-tips
        >
          {{ item.module_name }}
        </div>
        <div
          class="column env"
          v-bk-overflow-tips
        >
          {{ item.environment === 'stag' ? $t('预发布环境') : $t('生产环境') }}
        </div>
      </li>
      <div class="list-footer">
        <div class="all-count mr10">
          {{ $t('共计 {n} 条', { n: config.bound_app_module_envs?.length }) }}
        </div>
        <bk-pagination
          small
          :current.sync="pagination.current"
          :count.sync="pagination.count"
          :limit="pagination.limit"
          :limit-list="pagination.limitList"
          @change="handlePageChange"
          @limit-change="handlePageLimitChange"
        />
      </div>
    </ul>
    <div class="flex-row justify-content-center mt15">
      <bk-button
        :theme="'default'"
        style="width: 88px"
        @click="close"
      >
        {{ $t('关闭') }}
      </bk-button>
    </div>
  </bk-dialog>
</template>

<script>
import { paginationFun } from '@/common/utils';
export default {
  name: 'DeleteClusterAlertDialog',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    clusterName: {
      type: String,
      default: '',
    },
    config: {
      type: Object,
      default: () => ({}),
    },
  },
  data() {
    return {
      pagination: {
        current: 1,
        count: 0,
        limit: 5,
        limitList: [5, 10],
      },
    };
  },
  computed: {
    dialogVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    boundAppLegth() {
      return this.config.bound_app_module_envs?.length || 0;
    },
    deletePromptOne() {
      return this.$t('1. 被 {s} 等 <i>{n}</i> 个租户使用，请先在集群配置页面，解除租户与集群的分配关系。', {
        s: this.config.allocated_tenant_ids?.join('、'),
        n: this.config.allocated_tenant_ids?.length,
      });
    },
    deletePromptTwo() {
      let prefix = '2. ';
      if (this.config.allocated_tenant_ids?.length < 1) {
        prefix = '1. ';
      }
      return prefix + this.$t('被 <i>{n}</i> 个应用模块绑定', { n: this.boundAppLegth });
    },
    displayBoundApps() {
      const { current, limit } = this.pagination;
      const { pageData } = paginationFun(this.config.bound_app_module_envs, current, limit);
      return pageData;
    },
  },
  methods: {
    close() {
      this.dialogVisible = false;
    },
    handlePageLimitChange(limit) {
      this.pagination.limit = limit;
      this.pagination.current = 1;
    },
    handlePageChange(page) {
      this.pagination.current = page;
    },
    valueChange(flag) {
      if (flag) {
        this.pagination.count = this.boundAppLegth;
      }
    },
    dialogAfterLeave() {
      this.pagination = {
        current: 1,
        count: 0,
        limit: 5,
        limitList: [5, 10, 20, 50],
      };
    },
  },
};
</script>

<style lang="scss" scoped>
/deep/ .del-cluster-dialog-cls {
  .bk-dialog-body {
    padding: 3px 48px 24px;
  }
  .dialog-title {
    display: flex;
    flex-direction: column;
    align-items: center;
    margin-bottom: 26px;
    .icon-wrapper {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 42px;
      height: 42px;
      background-color: #ffe8c3;
      border-radius: 50%;
    }
    p {
      height: 32px;
      font-size: 20px;
      color: #313238;
    }
    i {
      color: #ff9c01;
      font-size: 26px;
    }
  }
  .del-alert-info-content {
    margin-top: 12px;
    text-align: left;
    padding: 12px 16px;
    font-size: 12px;
    border-radius: 2px;
    line-height: 22px;
    color: #4d4f56;
    background: #f5f6fa;
  }
  .bound-apps {
    position: relative;
    color: #313238;
    font-size: 12px;
    border: 1px solid #eaebf0;
    .paasng-general-copy {
      position: absolute;
      right: 16px;
      top: 10px;
      cursor: pointer;
      color: #3a84ff;
    }
    .list-title {
      height: 32px;
      background: #f0f1f5 !important;
    }
    .list-footer {
      display: flex;
      align-items: center;
      height: 42px;
      padding: 0 16px;
      color: #4d4f56;
      border-top: 1px solid #eaebf0;
      .all-count {
        flex-shrink: 0;
      }
      .bk-page {
        width: 100%;
        .bk-page-count {
          margin-top: 0;
        }
      }
      .bk-select {
        line-height: 24px;
        height: 24px;
      }
    }
    .app-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 0 16px;
      height: 32px;
      &:nth-child(odd) {
        background: #fafbfd;
      }
      .column {
        overflow: hidden;
        white-space: nowrap;
        text-overflow: ellipsis;
      }
      .module {
        width: 120px;
      }
      .env {
        width: 80px;
      }
      .app-id {
        flex: 1;
      }
    }
  }
  .dialog-delete-info {
    font-size: 12px;
    i {
      color: #eb3131;
      font-weight: 700;
      padding: 0 3px;
      font-style: normal;
    }
  }
}
</style>
