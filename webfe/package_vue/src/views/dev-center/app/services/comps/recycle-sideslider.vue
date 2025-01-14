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
          <p class="recycle-tips">{{ $t('共有 {n} 个增强服务实例未回收', { n: count }) }}</p>
          <div>
            <bk-radio-group
              v-model="activeInstance"
              @change="handlerChange"
            >
              <bk-radio-button
                v-for="(item, index) in list"
                :value="item.service?.uuid"
                :key="index"
              >
                {{ item.service?.display_name }}
              </bk-radio-button>
            </bk-radio-group>
          </div>
        </div>
        <!-- 根据实例切换 -->
        <bk-table
          :data="instanceList"
          v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
          size="large"
          style="margin-top: 24px"
          ext-cls="instance-details-table-cls"
        >
          <!-- 文案调整！！！！！ -->
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
              <template
                v-if="row.service_instance.config.hasOwnProperty('is_done') && !row.service_instance.config.is_done"
              >
                <p class="mt15 mb15">
                  {{ $t('服务正在创建中，请通过“管理入口”查看进度') }}
                </p>
              </template>
              <template v-else>
                <section class="credential-information">
                  <div
                    v-for="(value, key) in row.service_instance.credentials"
                    :key="key"
                    class="config-width"
                    v-bk-overflow-tips
                  >
                    <span class="gray">{{ key }}:</span>
                    <span class="break-all">{{ value }}</span>
                    <br />
                  </div>
                  <div
                    v-for="(key, fieldsIndex) in row.service_instance.sensitive_fields"
                    :key="fieldsIndex"
                  >
                    <span class="gray">{{ key }}:</span>
                    <span v-if="sensitiveFields[row.instance_id]">
                      {{ sensitiveFields[row.instance_id][key] }}
                      <i
                        class="paasng-icon paasng-general-copy copy-icon"
                        v-copy="sensitiveFields[row.instance_id][key]"
                      />
                    </span>
                    <span v-else>
                      <span>******</span>
                      <i
                        class="paasng-icon paasng-eye-slash view-password"
                        v-bk-tooltips="platformFeature.VERIFICATION_CODE ? $t('验证查看') : $t('点击查看')"
                        @click="hanldleViewSecret(row, key)"
                      />
                    </span>
                  </div>
                  <div
                    v-for="(value, key) in row.service_instance.hidden_fields"
                    :key="key"
                    v-bk-overflow-tips
                  >
                    <span class="gray">{{ key }}:</span>
                    <span
                      v-if="hFieldstoggleStatus[$index][key]"
                      class="break-all"
                    >
                      {{ value }}
                    </span>
                    <span
                      v-else
                      class="break-all"
                    >
                      ******
                    </span>
                    <button
                      v-bk-tooltips="$t('敏感字段，点击后显示')"
                      class="btn-display-hidden-field ps-btn ps-btn-default ps-btn-xs"
                      @click="$set(hFieldstoggleStatus[$index], key, !hFieldstoggleStatus[$index][key])"
                    >
                      {{ hFieldstoggleText[hFieldstoggleStatus[$index][key] || false] }}
                    </button>
                  </div>
                </section>
                <div
                  v-if="!row.service_instance.sensitive_fields.length"
                  class="copy-container"
                >
                  <i
                    class="paasng-icon paasng-general-copy"
                    v-copy="handleCopy(row)"
                  />
                </div>
              </template>
            </template>
          </bk-table-column>
          <bk-table-column
            :label="$t('使用环境')"
            prop="ip"
          >
            <template slot-scope="{ row }">
              {{ row.environment_name }}
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
    <!-- 回收增强服务 -->
    <bk-dialog
      v-model="recycleyDialog.visible"
      theme="primary"
      :width="480"
      :mask-close="false"
      header-position="left"
      :title="$t('确认回收增强服务')"
      ext-cls="recycle-dialog-cls"
      @after-leave="recycleyDialog.appCode = ''"
    >
      <div class="content">
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
              <span>{{ $t('增强服务实例将被永久删除，无法恢复，如有需要务必先自行备份数据。') }}</span>
              <!-- <bk-button
                text
                size="small"
              >
                {{ $t('增强服务数据备份指引') }}
              </bk-button> -->
            </div>
          </div>
        </bk-alert>
        <div class="label">
          {{ $t('请完整输入应用 ID ') }}
          <code>{{ appCode }}</code>
          {{ $t('确认：') }}
        </div>
        <bk-input v-model="recycleyDialog.appCode"></bk-input>
      </div>
      <template slot="footer">
        <bk-button
          theme="primary"
          :loading="recycleyDialog.isLoading"
          :disabled="!recycleValidated"
          @click="submitRecycleInstance"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          theme="default"
          @click="recycleyDialog.visible = false"
        >
          {{ $t('取消') }}
        </bk-button>
      </template>
    </bk-dialog>

    <!-- 获取验证码 -->
    <VerificationCodeDialog
      :show.sync="isVerificationCodeDialog"
      func="RETRIEVE_UNBOUND_SERVICE_SENSITIVE_FIELD"
      @confirm="handleDialogConfirm"
    />
  </div>
</template>

<script>
import VerificationCodeDialog from '@/components/verification-code-dialog';
export default {
  name: 'RecycleSideslider',
  components: { VerificationCodeDialog },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    list: {
      type: Array,
      default: () => [],
    },
    count: {
      type: Number,
      default: 0,
    },
  },
  data() {
    return {
      activeInstance: '',
      activeInstanceData: {},
      isTableLoading: false,
      instanceList: [],
      hFieldstoggleStatus: [],
      hFieldstoggleText: {
        true: this.$t('隐藏'),
        false: this.$t('显示'),
      },
      recycleyDialog: {
        visible: false,
        isLoading: false,
        appCode: '',
        row: {},
      },
      viewSecretData: {},
      isVerificationCodeDialog: false,
      // 敏感字段
      sensitiveFields: {},
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
      return this.$route.params.id;
    },
    curAppModule() {
      return this.$store.state.curAppModule;
    },
    curModuleId() {
      return this.curAppModule?.name;
    },
    recycleValidated() {
      return this.appCode === this.recycleyDialog.appCode;
    },
    platformFeature() {
      return this.$store.state.platformFeature;
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
      this.sensitiveFields = {};
    },
    handlerChange(active) {
      // 切换对应服务实例详情
      this.setInstance(active);
    },
    // 设置默认数据
    setInstance(active) {
      this.activeInstance = active;
      this.activeInstanceData = this.list.find((v) => v.service?.uuid === active) || {};
      this.instanceList = this.activeInstanceData.unbound_instances || [];
      this.hFieldstoggleStatus = this.instanceList.map(() => ({}));
    },
    reset() {
      this.activeInstance = '';
      this.activeInstanceData = {};
      this.instanceList = [];
      this.hFieldstoggleStatus = [];
    },
    // 回收弹窗确认
    handleRecycle(row) {
      this.recycleyDialog.visible = true;
      this.recycleyDialog.row = row;
    },
    // 确认回收服务
    submitRecycleInstance() {
      const uuid = this.activeInstanceData.service?.uuid;
      const instanceId = this.recycleyDialog.row.instance_id;
      this.recycleyDialog.visible = false;
      this.recyclingService(uuid, instanceId);
    },
    // 处理复制内容
    handleCopy(payload) {
      const { credentials } = payload.service_instance;
      const hiddenFields = payload.service_instance.hidden_fields;
      let copyContent = '';
      for (const key in credentials) {
        copyContent += `${key}:${credentials[key]}\n`;
      }
      for (const key in hiddenFields) {
        copyContent += `${key}:${hiddenFields[key]}\n`;
      }
      return copyContent;
    },
    // 启停Loading
    toggleLoading(loading) {
      this.isTableLoading = loading;
    },
    // 回收增强服务实例
    async recyclingService(serviceId, instanceId) {
      this.recycleyDialog.isLoading = true;
      try {
        await this.$store.dispatch('service/recyclingService', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          serviceId,
          instanceId,
        });
        // 刷新服务列表
        this.$emit('refresh');
        this.$paasMessage({
          theme: 'success',
          message: this.$t('回收成功'),
        });
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.recycleyDialog.isLoading = false;
      }
    },
    // 查看敏感字段
    hanldleViewSecret(row, key) {
      this.viewSecretData = row;
      this.viewSecretData.fieldName = key;
      if (!this.platformFeature.VERIFICATION_CODE) {
        // 无需要获取验证码校验，直接请求
        this.submitVerificationCode();
        return;
      }
      this.showVerificationCodeDialog();
    },
    // 获取验证码弹窗
    showVerificationCodeDialog() {
      this.isVerificationCodeDialog = true;
    },
    handleDialogConfirm(code) {
      this.submitVerificationCode(code);
    },
    //  提交验证码获取敏感信息字段
    async submitVerificationCode(code = '') {
      try {
        const data = {
          instance_id: this.viewSecretData.instance_id,
          field_name: this.viewSecretData.fieldName,
          // VERIFICATION_CODE 为 true 需要发验证码
          ...(this.platformFeature.VERIFICATION_CODE && { verification_code: code }),
        };
        const res = await this.$store.dispatch('service/queryUnbindInstanceSensitiveFields', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          serviceId: this.activeInstanceData.service?.uuid,
          data,
        });
        const field = { [this.viewSecretData.fieldName]: res };
        this.$set(this.sensitiveFields, this.viewSecretData.instance_id, field);
      } catch (e) {
        this.catchErrorHandler(e);
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
    margin-top: -12px;
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
.recycle-dialog-cls {
  .paasng-remind {
    transform: translateY(0px);
    font-size: 14px;
    color: #ea3636;
  }
  .label {
    line-height: 22px;
    color: #4d4f56;
    margin-top: 24px;
    margin-bottom: 6px;
  }
}
.recycle-alert-cls {
  margin-bottom: 16px;
  .paasng-remind {
    margin-right: 9px;
  }
  .bk-button-text {
    line-height: 1 !important;
    height: 12px !important;
    padding: 0;
  }
}
</style>
