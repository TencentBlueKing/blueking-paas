<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    show-mask
    width="960"
    @shown="shown"
    @hidden="reset"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ isAdd ? $t('新建方案') : $t('编辑方案') }}</span>
        <span class="desc">{{ `${$t('租户')}：${tenantId}` }}</span>
      </div>
    </div>
    <div
      class="sideslider-content"
      slot="content"
    >
      <bk-form
        ref="formRef"
        form-type="vertical"
        :model="formData"
      >
        <bk-form-item
          v-for="item in formItems"
          :label="$t(item.label)"
          :required="$t(item.required)"
          :property="item.property"
          :rules="item.rules"
          :key="item.label"
        >
          <bk-input
            v-model="formData[item.property]"
            v-if="item.type === 'input'"
          ></bk-input>
          <bk-select
            v-else-if="item.type === 'select'"
            v-model="formData[item.property]"
            :disabled="!isAdd"
            searchable
          >
            <bk-option
              v-for="option in services"
              :id="option.name"
              :name="`${option.display_name} (${option.name})`"
              :key="option.uuid"
            ></bk-option>
          </bk-select>
          <bk-switcher
            v-else-if="item.type === 'switcher'"
            theme="primary"
            v-model="formData[item.property]"
          ></bk-switcher>
        </bk-form-item>
        <bk-form-item
          :label="$t('配置')"
          :required="true"
          property="config"
        >
          <!-- JSON编辑器 -->
          <div class="editor-wrapper">
            <JsonEditorVue
              class="pt-json-editor-custom-cls"
              ref="jsonEditor"
              style="width: 100%; height: 100%"
              v-model="valuesJson"
              :debounce="20"
              :mode="'text'"
            />
          </div>
          <!-- 配置示例 -->
          <ConfigExample
            v-if="curServiceSchema"
            :schema="curServiceSchema"
          />
        </bk-form-item>
      </bk-form>
      <section class="footer-btns">
        <bk-button
          style="margin-right: 8px"
          ext-cls="btn-cls"
          theme="primary"
          @click="submitData"
        >
          {{ $t('提交') }}
        </bk-button>
        <bk-button
          ext-cls="btn-cls"
          theme="default"
          @click="close"
        >
          {{ $t('取消') }}
        </bk-button>
      </section>
    </div>
  </bk-sideslider>
</template>

<script>
import JsonEditorVue from 'json-editor-vue';
import { validateJson } from '../validators';
import ConfigExample from './config-example.vue';
export default {
  name: 'EditAddSideslider',
  components: {
    JsonEditorVue,
    ConfigExample,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    config: {
      type: Object,
      default: () => ({}),
    },
    data: {
      type: Object,
      default: () => ({}),
    },
    // 所属服务
    services: {
      type: Array,
      default: () => [],
    },
    tenantId: {
      type: String,
      default: '',
    },
    serviceName: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      // 保存按钮loading
      saveLoading: false,
      formData: {
        name: '',
        // 所属服务
        service_name: '',
        description: '',
        // 是否可见
        is_active: true,
        // 方案配置
        config: {},
      },
      formItems: Object.freeze([
        {
          property: 'name',
          label: '名称',
          type: 'input',
          required: true,
          rules: [
            {
              required: true,
              message: this.$t('请输入'),
              trigger: 'blur',
            },
          ],
        },
        {
          property: 'service_name',
          label: '所属服务',
          type: 'select',
          required: true,
          rules: [
            {
              required: true,
              message: this.$t('请选择'),
              trigger: 'blur',
            },
          ],
        },
        {
          property: 'description',
          label: '简介',
          type: 'input',
          required: true,
          rules: [
            {
              required: true,
              message: this.$t('请输入'),
              trigger: 'blur',
            },
          ],
        },
        { property: 'is_active', label: '可见', type: 'switcher', required: true },
      ]),
      valuesJson: {},
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
    isAdd() {
      return this.config.type === 'add';
    },
    // 当前服务的方案配置示例
    curServiceSchema() {
      return this.services.find((v) => v.name === this.formData.service_name)?.plan_schema;
    },
  },
  methods: {
    close() {
      this.sidesliderVisible = false;
      this.reset();
    },
    reset() {
      this.formData = {
        name: '',
        service_name: '',
        description: '',
        is_active: true,
        config: {},
      };
      this.valuesJson = {};
      this.saveLoading = false;
    },
    shown() {
      this.formData.service_name = this.serviceName || '';
      if (!this.isAdd) {
        // 编辑回填
        const { name, service_name, description, is_active, config } = this.data;
        this.formData = {
          name,
          service_name,
          description,
          is_active,
          config,
        };
        this.$nextTick(() => {
          this.valuesJson = config;
        });
      }
    },
    handleInput(code) {
      // 编辑后的内容
      this.formData.config = JSON.parse(code);
    },
    // 提交-校验
    submitData() {
      this.$refs.formRef?.validate().then(
        () => {
          // JSON校验
          const validateResult = validateJson(this.valuesJson, this.$refs.jsonEditor?.jsonEditor);
          if (!validateResult) {
            return;
          }
          this.saveLoading = true;
          const params = {
            ...this.formData,
            config: typeof this.valuesJson === 'string' ? JSON.parse(this.valuesJson) : this.valuesJson,
          };
          delete params.service_name;
          const id = this.services.find((v) => v.name === this.formData.service_name)?.uuid;
          if (this.isAdd) {
            // 新建
            this.addPlan(id, params);
            return;
          }
          // 编辑
          const { uuid } = this.data;
          this.modifyPlan(id, uuid, params);
        },
        (e) => {
          console.warn(e);
        }
      );
    },
    // 新建方案
    async addPlan(serviceId, data) {
      try {
        await this.$store.dispatch('tenant/addPlan', {
          serviceId,
          tenantId: this.tenantId, // 使用下拉框数据
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('添加成功'),
        });
        this.close();
        // 通知外界更新
        this.$emit('refresh');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.saveLoading = false;
      }
    },
    // 编辑方案
    async modifyPlan(serviceId, planId, data) {
      try {
        await this.$store.dispatch('tenant/modifyPlan', {
          serviceId,
          tenantId: this.tenantId,
          planId,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('编辑成功'),
        });
        this.close();
        // 通知外界更新
        this.$emit('refresh');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.saveLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.header-box {
  .desc {
    height: 22px;
    margin-left: 10px;
    padding-left: 8px;
    font-size: 14px;
    color: #979ba5;
    border-left: 1px solid #dcdee5;
  }
}
.sideslider-content {
  padding: 24px 40px;
  .btn-cls {
    min-width: 88px;
  }
  .editor-wrapper {
    height: 350px;
    /deep/ .jsoneditor-vue {
      height: 100%;
    }
  }
  .footer-btns {
    margin-top: 26px;
  }
}
</style>
