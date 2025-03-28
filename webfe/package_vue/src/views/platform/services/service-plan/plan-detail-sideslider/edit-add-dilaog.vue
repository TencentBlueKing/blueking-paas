<template>
  <bk-dialog
    v-model="dialogVisible"
    width="640"
    :theme="'primary'"
    :header-position="'left'"
    :mask-close="false"
    :auto-close="false"
    render-directive="if"
    :title="isAdd ? $t('添加实例') : $t('编辑实例')"
    @value-change="valueChange"
  >
    <div slot="footer">
      <bk-button
        theme="primary"
        :loading="dialogLoading"
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
        class="mb16"
        type="info"
        :title="
          $t('实例配置将以环境变量方式注入至应用运行时环境（每个配置项将添加 {n} 前缀，且会转换成全大写字母）', {
            n: this.data.service,
          })
        "
        closable
      ></bk-alert>
      <bk-form
        ref="formRef"
        :label-width="200"
        form-type="vertical"
      >
        <bk-form-item
          :label="$t('可回收复用')"
          :required="true"
        >
          <bk-switcher
            theme="primary"
            v-model="formData.recyclable"
          ></bk-switcher>
        </bk-form-item>
        <bk-form-item
          :label="$t('实例配置')"
          :required="true"
        >
          <div class="json-editor-wrapper">
            <VueJsonEditor
              style="width: 100%; height: 100%"
              v-model="valuesJson"
              :mode="'code'"
              :modes="['code', 'tree', 'text']"
              :expanded-on-start="true"
              @json-change="handleJsonUpdate"
              @has-error="handleError"
            />
          </div>
        </bk-form-item>
      </bk-form>
    </div>
  </bk-dialog>
</template>

<script>
import VueJsonEditor from 'vue-json-editor';
export default {
  name: 'SandboxDialog',
  components: {
    VueJsonEditor,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      formData: {
        recyclable: true,
        config: {},
      },
      valuesJson: {},
      dialogLoading: false,
      hasJsonFlag: true,
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
    isAdd() {
      return this.data.type === 'add';
    },
  },
  methods: {
    valueChange(flag) {
      this.dialogLoading = false;
      if (flag && !this.isAdd) {
        const { row = {} } = this.data;
        this.formData.recyclable = !!Object.keys(row.config)?.length;
        this.valuesJson = JSON.parse(row.credentials);
      } else {
        this.valuesJson = {};
        this.formData = {
          recyclable: true,
          config: {},
        };
      }
    },
    close() {
      this.dialogVisible = false;
    },
    // 确认
    handleConfirm() {
      this.$refs.formRef
        ?.validate()
        .then(() => {
          if (!this.hasJsonFlag) return;
          // this.dialogLoading = true;
          const params = {
            plan: this.data.planId,
            // 实例配置：JSON格式
            credentials: JSON.stringify(this.valuesJson),
            // 可回收复用：：开启：{config: {recycle:true} } / 停用：{}
            config: this.formData.recyclable ? { recycle: true } : {},
          };
          if (this.isAdd) {
            this.addResourcePool(params);
          } else {
            this.updateResourcePool(params);
          }
        })
        .catch((e) => {
          console.warn(e);
        });
    },
    // json 更新
    handleJsonUpdate(updatedJson) {
      this.valuesJson = updatedJson;
      this.hasJsonFlag = true;
    },
    // json 编辑错误
    handleError(errorMessage) {
      this.hasJsonFlag = false;
      console.warn('JSON 校验失败:', errorMessage);
    },
    // 添加资源池
    async addResourcePool(data) {
      try {
        await this.$store.dispatch('tenant/addResourcePool', {
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('添加成功'),
        });
        this.$emit('refresh', true);
        // 关闭弹窗
        this.close();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.dialogLoading = false;
      }
    },
    // 编辑资源池
    async updateResourcePool(data) {
      try {
        const { planId, row } = this.data;
        await this.$store.dispatch('tenant/updateResourcePool', {
          planId,
          id: row.uuid,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('编辑成功'),
        });
        this.$emit('refresh', true);
        // 关闭弹窗
        this.close();
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.dialogLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.dialog-content {
  .mb16 {
    margin-bottom: 16px;
  }
  .json-editor-wrapper {
    height: 350px;
    /deep/ .jsoneditor-vue {
      height: 100%;
    }
  }
}
</style>
