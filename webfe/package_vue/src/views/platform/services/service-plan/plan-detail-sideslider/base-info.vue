<template>
  <div class="plan-base-info-container">
    <bk-button
      v-if="!isEdit"
      class="edit-btns"
      theme="primary"
      :outline="true"
      @click="handleEdit"
    >
      {{ $t('编辑') }}
    </bk-button>
    <!-- 查看模式 -->
    <template v-if="!isEdit">
      <DetailsRow
        v-for="(val, key) in baseInfoMap"
        :key="val"
        :label-width="80"
        :label="`${val}：`"
        :class="key"
      >
        <div
          v-if="key === 'config'"
          slot="value"
          class="json-pretty"
        >
          <vue-json-pretty
            class="paas-vue-json-pretty-cls"
            :data="data[key]"
            :show-length="true"
            :expanded="Object.keys(data[key])?.length"
            :highlight-mouseover-node="true"
          />
        </div>
        <div
          v-else-if="key === 'is_active'"
          slot="value"
        >
          <span :class="['tag', { yes: data[key] }]">{{ data[key] ? $t('是') : $t('否') }}</span>
        </div>
        <div
          v-else
          slot="value"
        >
          {{ data[key] }}
        </div>
      </DetailsRow>
    </template>
    <!-- 编辑模式 -->
    <template v-else>
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
            :disabled="true"
            searchable
          >
            <bk-option
              v-for="option in services"
              :id="option.name"
              :name="option.name"
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
          :label="$t('方案配置')"
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
        </bk-form-item>
      </bk-form>
      <section class="footer-btns">
        <bk-button
          style="margin-right: 8px"
          ext-cls="btn-cls"
          theme="primary"
          :loading="saveLoading"
          @click="submitData"
        >
          {{ $t('提交') }}
        </bk-button>
        <bk-button
          ext-cls="btn-cls"
          theme="default"
          @click="handleCancel"
        >
          {{ $t('取消') }}
        </bk-button>
      </section>
    </template>
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
import JsonEditorVue from 'json-editor-vue';
import { validateJson } from '../../validators';
export default {
  props: {
    data: {
      type: Object,
      default: () => ({}),
    },
    // 所属服务
    services: {
      type: Array,
      default: () => [],
    },
    // 所属服务
    tenantId: {
      type: String,
      default: '',
    },
  },
  components: {
    DetailsRow,
    VueJsonPretty,
    JsonEditorVue,
  },
  data() {
    return {
      baseInfoMap: {
        name: this.$t('方案名称'),
        service_name: this.$t('所属服务'),
        description: this.$t('方案简介'),
        is_active: this.$t('是否可见'),
        config: this.$t('方案配置'),
      },
      isEdit: false,
      saveLoading: false,
      valuesJson: {},
      formData: {
        name: '',
        // 所属服务
        service_name: '',
        description: '',
        is_active: true,
        // 方案配置
        config: {},
      },
      formItems: Object.freeze([
        {
          property: 'name',
          label: '方案名称',
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
          label: '方案简介',
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
    };
  },
  methods: {
    handleEdit() {
      this.isEdit = true;
      this.fillFormData();
    },
    // 数据回填
    fillFormData() {
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
    },
    // 编辑方案
    async modifyPlan(id, planId, data) {
      try {
        await this.$store.dispatch('tenant/modifyPlan', {
          id,
          planId,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('编辑成功'),
        });
        this.$emit('change-details', data);
        this.handleCancel();
        // 通知外界更新
        this.$emit('operate');
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.saveLoading = false;
      }
    },
    // 提交-校验
    submitData() {
      this.$refs.formRef
        ?.validate()
        .then(() => {
          // 基础JSON校验
          const validateResult = validateJson(this.valuesJson, this.$refs.jsonEditor?.jsonEditor);
          if (!validateResult) {
            return;
          }
          this.saveLoading = true;
          const params = {
            ...this.formData,
            tenant_id: this.tenantId,
            config: typeof this.valuesJson === 'string' ? JSON.parse(this.valuesJson) : this.valuesJson,
          };
          delete params.service_name;
          const id = this.services.find((v) => v.name === this.formData.service_name)?.uuid;
          const { uuid } = this.data;
          this.modifyPlan(id, uuid, params);
        })
        .catch((e) => {
          console.warn(e);
        });
    },
    handleCancel() {
      this.isEdit = false;
      this.valuesJson = {};
    },
  },
};
</script>

<style lang="scss" scoped>
.plan-base-info-container {
  position: relative;
  /deep/ .details-row.config .value {
    width: 100%;
  }
  .json-pretty {
    padding: 8px;
    background: #f5f7fa;
    border-radius: 2px;
  }
  .edit-btns {
    position: absolute;
    right: 0;
    top: 8px;
  }
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
