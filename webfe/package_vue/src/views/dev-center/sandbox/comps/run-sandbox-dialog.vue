<template>
  <bk-dialog
    v-model="dialogVisible"
    width="480"
    :theme="'primary'"
    :header-position="'left'"
    :mask-close="false"
    :auto-close="false"
    render-directive="if"
    :title="$t('运行沙箱环境')"
  >
    <div slot="footer">
      <bk-button
        theme="primary"
        @click="handleConfirm"
      >
        {{ $t('确定') }}
      </bk-button>
      <bk-button
        :theme="'default'"
        type="submit"
        class="ml8"
        @click="dialogVisible = false"
      >
        {{ $t('取消') }}
      </bk-button>
    </div>
    <div class="dialog-content">
      <bk-alert
        type="warning"
        class="sandbox-alert-cls"
      >
        <div slot="title">
          <span>
            {{ $t('沙箱环境将复用了预发布环境的增强服务，启用 Celery 等后台进程会影响预发布环境的任务执行。') }}
          </span>
          <!-- <bk-button
            :theme="'primary'"
            text
            size="small"
            ext-cls="alert-btn-cls"
          >
            {{ $t('如何修改沙箱启动进程') }}
          </bk-button> -->
        </div>
      </bk-alert>
      <div class="process-box">
        <div class="title">{{ $t('进程列表') }}</div>
        <ul class="processs">
          <li
            class="item"
            v-for="(process, index) in processData"
            :key="index"
          >
            {{ process.name }}
          </li>
        </ul>
      </div>
    </div>
  </bk-dialog>
</template>

<script>
export default {
  name: 'RunSandboxDialog',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    processData: {
      type: Object,
      default: () => [],
    },
  },
  data() {
    return {};
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
  },
  methods: {
    handleConfirm() {
      this.dialogVisible = false;
      this.$emit('confirm');
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-content {
  .alert-btn-cls {
    padding: 0 !important;
  }
  .process-box {
    .title {
      color: #63656e;
      margin: 16px 0 8px;
    }
    .processs .item {
      height: 32px;
      line-height: 32px;
      margin-bottom: 10px;
      background: #fafbfd;
      border-radius: 2px;
      padding: 0 15px;
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
}
</style>
