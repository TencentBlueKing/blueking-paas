<template>
  <div>
    <bk-sideslider
      :is-show.sync="sidesliderVisible"
      :quick-close="true"
      width="960"
      :title="$t('未回收的增强服务实例')"
      @shown="handleShown"
    >
      <div
        class="sideslider-content"
        slot="content"
      >
        <div class="top-container">
          <p class="recycle-tips">{{ $t('共有 {n} 个增强服务实例未回收', { n: list.length }) }}</p>
          <!-- 服务 tab -->
          <bk-radio-group
            v-model="activeInstance"
            @change="handlerChange"
          >
            <bk-radio-button
              v-for="(item, index) in groupData"
              :value="item?.id"
              :key="index"
            >
              {{ item?.displayName }}
            </bk-radio-button>
          </bk-radio-group>
        </div>
        <!-- 根据实例切换 -->
        <bk-table
          :data="activeInstanceList"
          size="large"
          style="margin-top: 24px"
          ext-cls="instance-details-table-cls"
        >
          <div
            slot="empty"
            class="paas-loading-panel"
          >
            <div class="text">
              <table-empty
                class="table-empty-cls"
                :empty-title="$t('暂无未回收的增强服务实例')"
                empty
              />
            </div>
          </div>
          <bk-table-column
            :label="$t('实例 ID')"
            width="90"
          >
            <template slot-scope="{ $index }">#{{ $index + 1 }}</template>
          </bk-table-column>
          <bk-table-column
            :label="$t('凭证信息')"
            prop="ip"
            min-width="380"
          >
            <template slot-scope="{ row, $index }">
              <!-- 凭证信息 -->
              <section class="credential-information">
                <div
                  v-for="(value, key) in row.instance?.credentials"
                  :key="key"
                  class="config-width"
                  v-bk-overflow-tips
                >
                  <span class="gray">{{ key }}:</span>
                  <span class="break-all">{{ value }}</span>
                  <br />
                </div>
              </section>
              <div class="copy-container">
                <i
                  class="paasng-icon paasng-general-copy"
                  v-copy="handleCopy(row)"
                />
              </div>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('使用环境')"
            prop="ip"
          >
            <template slot-scope="{ row }">
              {{ row.environment === 'prod' ? $t('生产环境') : $t('预发布环境') }}
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('操作')"
            :width="120"
          >
            <template slot-scope="{ row }">
              <bk-button
                :text="true"
                title="primary"
                @click="handleRecycle(row)"
              >
                {{ $t('回收') }}
              </bk-button>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </bk-sideslider>

    <DeleteDialog
      :show.sync="recycleyDialog.visible"
      :title="$t('确认回收增强服务')"
      :expected-confirm-text="appCode"
      :loading="recycleyDialog.isLoading"
      @confirm="recycleServiceInstance"
    >
      <div class="hint-text mt8">
        <bk-alert
          type="error"
          :show-icon="false"
          class="recycle-alert-cls"
        >
          <div
            slot="title"
            class="flex-row"
          >
            <i class="paasng-icon paasng-remind"></i>
            <div>
              <span>{{ $t('回收后，增强服务实例将被永久删除，无法恢复。回收前可自助备份数据。') }}</span>
            </div>
          </div>
        </bk-alert>
        <span>{{ $t('请完整输入应用 ID') }}</span>
        <span>
          （
          <span class="sign">{{ appCode }}</span>
          <i
            class="paasng-icon paasng-general-copy"
            v-copy="appCode"
          />
          ）
        </span>
        {{ $t('进行确认') }}
      </div>
    </DeleteDialog>
  </div>
</template>

<script>
import DeleteDialog from '@/components/delete-dialog';

export default {
  name: 'PlatformRecycleSideslider',
  components: {
    DeleteDialog,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    list: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      activeInstance: '',
      recycleyDialog: {
        visible: false,
        isLoading: false,
        appCode: '',
        row: {},
      },
    };
  },
  computed: {
    sidesliderVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    appCode() {
      return this.$route.params.code;
    },
    platformFeature() {
      return this.$store.state.platformFeature;
    },
    // 未回收实例
    groupData() {
      const servicesMap = this.list.reduce((acc, item) => {
        const { uuid, display_name } = item.service;
        if (!acc[uuid]) {
          acc[uuid] = { id: uuid, displayName: display_name };
        }
        return acc;
      }, {});
      return Object.values(servicesMap);
    },
    // 当前实例table数据
    activeInstanceList() {
      return this.list.filter((instance) => instance.service?.uuid === this.activeInstance);
    },
  },
  watch: {
    list(newList) {
      if (newList.length) {
        this.setInstance(newList[0]?.service?.uuid ?? '');
      } else {
        this.reset();
      }
    },
  },
  methods: {
    handleShown() {
      if (this.list.length) {
        const fristInstance = this.list[0];
        this.setInstance(fristInstance.service?.uuid);
      }
    },
    // 切换对应服务实例详情
    handlerChange(active) {
      this.setInstance(active);
    },
    // 设置默认数据
    setInstance(active) {
      this.activeInstance = active;
    },
    reset() {
      this.activeInstance = '';
    },
    // 处理复制内容
    handleCopy(payload) {
      const { credentials } = payload.instance;
      let copyContent = '';
      for (const key in credentials) {
        copyContent += `${key}:${credentials[key]}\n`;
      }
      return copyContent;
    },
    // 回收弹窗确认
    handleRecycle(row) {
      this.toggleRecycleyDialog(true);
      this.recycleyDialog.row = row;
    },
    // 控制回收实例对话框的显示状态
    toggleRecycleyDialog(visible = false) {
      this.recycleyDialog.visible = visible;
    },
    // 回收增强服务实例
    async recycleServiceInstance() {
      this.recycleyDialog.isLoading = true;
      const { module, service, instance } = this.recycleyDialog.row;
      try {
        await this.$store.dispatch('tenantOperations/recycleServiceInstance', {
          appCode: this.appCode,
          moduleId: module,
          serviceId: service?.uuid,
          instanceId: instance?.uuid,
        });
        // 刷新服务列表
        this.$emit('refresh');
        this.$paasMessage({
          theme: 'success',
          message: this.$t('回收成功'),
        });
        this.toggleRecycleyDialog(false);
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.recycleyDialog.isLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.header-box {
  display: flex;
  justify-content: space-between;
}
.sideslider-content {
  padding: 24px;
  .recycle-tips {
    margin-bottom: 16px;
  }
}
.hint-text {
  .recycle-alert-cls {
    margin-bottom: 16px;
    font-size: 12px;
    color: #4d4f56;
    i.paasng-remind {
      margin-right: 9px;
      transform: translateY(0px);
      font-size: 14px;
      color: #ea3636;
    }
    .bk-button-text {
      line-height: 1 !important;
      height: 12px !important;
      padding: 0;
    }
  }
}
.instance-details-table-cls {
  .bk-table-row.bk-table-row-last td {
    border-bottom: none;
  }
  .credential-information {
    overflow: hidden;
    .copy-icon,
    .view-password {
      margin-left: 2px;
      font-size: 14px;
      cursor: pointer;
      &.paasng-eye-slash {
        transform: translateY(-3px);
        margin-left: 6px;
      }
      &:hover {
        color: #3a84ff;
      }
    }
  }
  .gray {
    color: #c4c6cc;
    margin-right: 6px;
  }
  .break-all {
    color: #63656e;
    font-size: 12px;
    line-height: 20px;
  }
  .paas-loading-panel .text {
    .sub-title {
      font-size: 12px;
    }
  }
  .copy-container {
    position: absolute;
    right: 45px;
    top: 50%;
    transform: translateY(-50%);
    color: #3a84ff;
    &:hover {
      cursor: pointer;
    }
  }
  .config-width {
    width: 85%;
    display: inline-block;
    white-space: nowrap;
    text-overflow: ellipsis;
    overflow: hidden;
  }
}
</style>
