<template>
  <bk-sideslider
    :is-show.sync="isShow"
    :width="640"
    :quick-close="true"
    :before-close="handleBeforeClose"
  >
    <div
      slot="header"
      class="flex-row align-items-center"
    >
      {{ isEdit ? $t('编辑方案') : $t('添加方案') }}
      <template v-if="isEdit">
        <bk-divider direction="vertical"></bk-divider>
        <span class="g-tip">{{ editData?.name }}</span>
      </template>
    </div>
    <div
      slot="content"
      class="quota-plan-content p-24"
      v-bkloading="{ isLoading: isLoading }"
    >
      <bk-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        form-type="vertical"
      >
        <bk-form-item
          :label="$t('CPU')"
          required
        >
          <div class="resource-row">
            <bk-form-item
              property="cpu_limit"
              class="inline-form-item"
            >
              <prefix-select
                v-model="formData.cpu_limit"
                width="288"
                prefix="Limits"
                :placeholder="$t('请选择')"
                :options="cpuOptions"
              />
            </bk-form-item>
            <bk-form-item
              property="cpu_request"
              class="inline-form-item ml16"
            >
              <prefix-select
                v-model="formData.cpu_request"
                width="288"
                prefix="Requests"
                :placeholder="$t('请选择')"
                :options="cpuOptions"
              />
            </bk-form-item>
          </div>
        </bk-form-item>

        <bk-form-item
          :label="$t('内存')"
          required
        >
          <div class="resource-row">
            <bk-form-item
              property="memory_limit"
              class="inline-form-item"
            >
              <prefix-select
                v-model="formData.memory_limit"
                width="288"
                prefix="Limits"
                :placeholder="$t('请选择')"
                :options="memoryOptions"
              />
            </bk-form-item>
            <bk-form-item
              property="memory_request"
              class="inline-form-item ml16"
            >
              <prefix-select
                v-model="formData.memory_request"
                width="288"
                prefix="Requests"
                :placeholder="$t('请选择')"
                :options="memoryOptions"
              />
            </bk-form-item>
          </div>
        </bk-form-item>

        <bk-form-item
          :label="$t('方案名称')"
          error-display-type="normal"
          property="name"
          required
        >
          <bk-input
            v-model="formData.name"
            :placeholder="$t('方案名称将以由 CPU/内存 Limit 自动生成，也可以自定义输入')"
            :maxlength="64"
          ></bk-input>
        </bk-form-item>

        <bk-form-item
          :label="$t('是否启用')"
          required
        >
          <bk-switcher
            v-model="formData.is_active"
            theme="primary"
          ></bk-switcher>
        </bk-form-item>
      </bk-form>
      <div class="mt-24">
        <bk-button
          class="mr-8"
          theme="primary"
          :loading="isSubmitting"
          @click="handleSubmit"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          @click="handleCancel"
          :disabled="isSubmitting"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </div>
  </bk-sideslider>
</template>

<script>
import PrefixSelect from '@/views/platform/operations/details/process/comps/prefix-select.vue';
import { convertMemoryToBytes } from '@/common/utils';

export default {
  name: 'QuotaPlanSideslider',
  components: {
    PrefixSelect,
  },
  props: {
    visible: {
      type: Boolean,
      default: false,
    },
    editData: {
      type: Object,
      default: null,
    },
    cpuOptions: {
      type: Array,
      default: () => [],
    },
    memoryOptions: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    // 通用必填校验规则
    const requiredRule = [
      {
        required: true,
        message: '必填项',
        trigger: 'blur',
      },
    ];

    // CPU Request 校验规则生成函数
    const createCpuRequestRule = () => [
      ...requiredRule,
      {
        validator: () => this.validateCpuRequest(),
        message: this.$t('Requests 不能大于 Limits'),
        trigger: 'change',
      },
    ];

    // 内存 Request 校验规则生成函数
    const createMemoryRequestRule = () => [
      ...requiredRule,
      {
        validator: () => this.validateMemoryRequest(),
        message: this.$t('Requests 不能大于 Limits'),
        trigger: 'change',
      },
    ];

    return {
      isLoading: false,
      isSubmitting: false,
      formData: {
        cpu_limit: '',
        cpu_request: '',
        memory_limit: '',
        memory_request: '',
        name: '',
        is_active: true,
      },
      // 表单校验规则
      formRules: {
        cpu_limit: requiredRule,
        cpu_request: createCpuRequestRule(),
        memory_limit: requiredRule,
        memory_request: createMemoryRequestRule(),
        name: requiredRule,
      },
    };
  },
  computed: {
    isShow: {
      get() {
        return this.visible;
      },
      set(val) {
        this.$emit('update:visible', val);
      },
    },
    isEdit() {
      return !!this.editData;
    },
  },
  watch: {
    visible(val) {
      if (val) {
        this.initFormData();
        if (!this.isEdit) {
          this.autoGenerateName();
        }
      }
    },
    'formData.cpu_limit'() {
      if (!this.isEdit) {
        this.autoGenerateName();
      }
      // 触发 CPU Request 校验
      this.$refs.formRef?.validateField('cpu_request').catch((e) => {
        console.error(`Validation error on field:`, e);
      });
    },
    'formData.memory_limit'() {
      if (!this.isEdit) {
        this.autoGenerateName();
      }
      // 触发内存 Request 校验
      this.$refs.formRef?.validateField('memory_request').catch((e) => {
        console.error(`Validation error on field:`, e);
      });
    },
  },
  methods: {
    // 初始化表单数据
    initFormData() {
      if (this.isEdit && this.editData) {
        // 编辑模式,填充现有数据(从嵌套结构中提取)
        this.formData = {
          cpu_limit: this.editData.limits?.cpu || '',
          cpu_request: this.editData.requests?.cpu || '',
          memory_limit: this.editData.limits?.memory || '',
          memory_request: this.editData.requests?.memory || '',
          name: this.editData.name || '',
          is_active: this.editData.is_active ?? true,
        };
      } else {
        // 新增模式,重置表单
        this.formData = {
          cpu_limit: '',
          cpu_request: '',
          memory_limit: '',
          memory_request: '',
          name: '',
          is_active: true,
        };
      }
      this.$nextTick(() => {
        this.$refs.formRef?.clearError();
      });
    },
    // 自动生成方案名称
    autoGenerateName() {
      const { cpu_limit, memory_limit } = this.formData;
      if (cpu_limit && memory_limit) {
        // 处理 CPU：所有 CPU 值都是 "xxxm" 格式，转换为核心数
        let cpuDisplay;
        if (cpu_limit.endsWith('m')) {
          const cpuMilliValue = parseInt(cpu_limit.replace('m', ''));
          const cpuCoreValue = cpuMilliValue / 1000;
          // 如果是整数核心数，显示整数；否则显示一位小数
          cpuDisplay = cpuCoreValue % 1 === 0 ? cpuCoreValue.toString() : cpuCoreValue.toFixed(1);
        } else {
          cpuDisplay = parseFloat(cpu_limit.replace(/[^0-9.]/g, '')).toString();
        }

        // 处理内存：所有内存值都是 "xxxMi" 格式
        let memoryDisplay;
        if (memory_limit.endsWith('Mi')) {
          const memoryMiValue = parseInt(memory_limit.replace('Mi', ''));
          if (memoryMiValue >= 1024 && memoryMiValue % 1024 === 0) {
            // 如果是 1024 的整数倍，转换为 G
            const gValue = memoryMiValue / 1024;
            memoryDisplay = `${gValue}G`;
          } else {
            // 否则保持 M 单位
            memoryDisplay = `${memoryMiValue}M`;
          }
        } else {
          memoryDisplay = memory_limit;
        }

        // 生成格式：0.1C256M, 1C1G, 4C2G 等
        this.formData.name = `${cpuDisplay}C${memoryDisplay}`;
      }
    },
    // 校验 CPU Requests 是否小于等于 Limits
    validateCpuRequest() {
      const { cpu_limit, cpu_request } = this.formData;
      if (!cpu_request || !cpu_limit) return true;
      // 将 CPU 值转换为数值进行比较(去除 'm' 单位)
      const requestNum = parseFloat(cpu_request.replace('m', ''));
      const limitNum = parseFloat(cpu_limit.replace('m', ''));
      return requestNum <= limitNum;
    },
    // 校验内存 Requests 是否小于等于 Limits
    validateMemoryRequest() {
      const { memory_limit, memory_request } = this.formData;
      if (!memory_request || !memory_limit) return true;
      // 将内存值转换为字节数进行比较
      const requestBytes = convertMemoryToBytes(memory_request);
      const limitBytes = convertMemoryToBytes(memory_limit);
      return requestBytes <= limitBytes;
    },
    // 关闭前确认
    handleBeforeClose() {
      if (this.isSubmitting) {
        return false;
      }
      return true;
    },
    // 提交
    async handleSubmit() {
      try {
        const isValid = await this.$refs.formRef
          .validate()
          .then(() => true)
          .catch(() => false);
        if (!isValid) return;

        this.isSubmitting = true;

        // 转换表单数据为接口需要的格式
        const payload = {
          name: this.formData.name,
          limits: {
            cpu: this.formData.cpu_limit,
            memory: this.formData.memory_limit,
          },
          requests: {
            cpu: this.formData.cpu_request,
            memory: this.formData.memory_request,
          },
          is_active: this.formData.is_active,
        };

        // 调用实际的 API
        if (this.isEdit) {
          // 编辑模式
          await this.$store.dispatch('tenantConfig/updateQuotaPlan', {
            id: this.editData.id,
            data: payload,
          });
        } else {
          // 新增模式
          await this.$store.dispatch('tenantConfig/createQuotaPlan', {
            data: payload,
          });
        }

        this.$paasMessage({
          theme: 'success',
          message: this.isEdit ? this.$t('编辑成功') : this.$t('添加成功'),
        });
        this.$emit('success');
        this.isShow = false;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isSubmitting = false;
      }
    },
    // 取消
    handleCancel() {
      this.isShow = false;
    },
  },
};
</script>

<style lang="scss" scoped>
.quota-plan-content {
  height: calc(100vh - 60px);
  overflow-y: auto;
}

.resource-row {
  display: flex;
  align-items: flex-start;
  /deep/ .bk-form-item {
    margin-top: 0 !important;
  }
}

.inline-form-item {
  flex: 1;
  margin-bottom: 0;

  &.ml16 {
    margin-left: 16px;
  }
}
</style>
