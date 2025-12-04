<template>
  <div class="resource-quota-container card-style">
    <div class="top-section flex-row align-items-center">
      <div class="title g-sub-title flex-shrink-0">{{ $t('资源配额') }}</div>
      <bk-button
        v-show="!isEdit"
        class="flex-shrink-0"
        :text="true"
        title="primary"
        @click="handleEdit"
      >
        {{ $t('编辑资源配额') }}
        <i class="paasng-icon paasng-edit-2"></i>
      </bk-button>
    </div>
    <!-- 查看态 -->
    <section
      v-if="!isEdit"
      class="view-mode-section"
    >
      <div class="flex-row align-items-start gap-24">
        <div
          v-for="env in envList"
          :key="env.key"
          class="env-container flex-1"
          :class="{ mr0: env.key === 'stag' }"
        >
          <div class="env-name">{{ env.label }}</div>
          <div class="env-form">
            <DetailsRow
              :label="`${$t('资源配额方案')}：`"
              :value="getPlanName(env.key)"
            />
            <DetailsRow
              label="CPU Limit："
              :value="formData[env.key].resources.limits.cpu || '--'"
            />
            <DetailsRow
              label="CPU Request："
              :value="formData[env.key].resources.requests.cpu || '--'"
            />
            <DetailsRow
              :label="`${$t('内存')} Limit：`"
              :value="formData[env.key].resources.limits.memory || '--'"
            />
            <DetailsRow
              :label="`${$t('内存')} Request：`"
              :value="formData[env.key].resources.requests.memory || '--'"
            />
          </div>
        </div>
      </div>
    </section>
    <!-- 编辑态 -->
    <section
      v-else
      class="edit-mode-section"
    >
      <div class="env-container">
        <div class="env-name">{{ $t('预发布环境') }}</div>
        <div class="env-form">
          <bk-form
            ref="stagForm"
            :label-width="120"
            :model="formData"
            :rules="formRules"
            ext-cls="env-form-cls"
          >
            <bk-form-item
              :label="$t('资源配额方案')"
              :required="true"
              :property="'stag.plan_name'"
              :error-display-type="'normal'"
            >
              <bk-select
                v-model="formData.stag.plan_name"
                style="width: 300px"
                ext-cls="plan-select-cls"
                @change="(value) => handlePlanChange(value, 'stag')"
              >
                <bk-option
                  v-for="option in planList"
                  :key="option.value"
                  :id="option.value"
                  :name="option.name"
                ></bk-option>
              </bk-select>
            </bk-form-item>
            <!-- CPU -->
            <div class="c-form-item-row flex-row align-items-center gap-16">
              <bk-form-item
                label="CPU"
                :required="true"
                :property="'stag.resources.limits.cpu'"
                :error-display-type="'normal'"
              >
                <div class="flex-row align-items-center gap-16">
                  <PrefixSelect
                    v-model="formData.stag.resources.limits.cpu"
                    prefix="Limit"
                    :options="cpuList"
                    :disabled="!isStagCustom"
                  />
                </div>
              </bk-form-item>
              <bk-form-item
                label=""
                :required="true"
                :property="'stag.resources.requests.cpu'"
                :error-display-type="'normal'"
              >
                <div class="flex-row align-items-center gap-16">
                  <PrefixSelect
                    v-model="formData.stag.resources.requests.cpu"
                    prefix="Request"
                    :options="cpuList"
                    :disabled="!isStagCustom"
                  />
                </div>
              </bk-form-item>
            </div>
            <!-- 内存 -->
            <div class="c-form-item-row flex-row align-items-center gap-16">
              <bk-form-item
                :label="$t('内存')"
                :required="true"
                :property="'stag.resources.limits.memory'"
                :error-display-type="'normal'"
              >
                <div class="flex-row align-items-center gap-16">
                  <PrefixSelect
                    v-model="formData.stag.resources.limits.memory"
                    prefix="Limit"
                    :options="memoryList"
                    :disabled="!isStagCustom"
                  />
                </div>
              </bk-form-item>
              <bk-form-item
                label=""
                :required="true"
                :property="'stag.resources.requests.memory'"
                :error-display-type="'normal'"
              >
                <div class="flex-row align-items-center gap-16">
                  <PrefixSelect
                    v-model="formData.stag.resources.requests.memory"
                    prefix="Request"
                    :options="memoryList"
                    :disabled="!isStagCustom"
                  />
                </div>
              </bk-form-item>
            </div>
          </bk-form>
        </div>
      </div>
      <!-- 生产环境 -->
      <div class="env-container mt-24">
        <div class="env-name">{{ $t('生产环境') }}</div>
        <div class="env-form">
          <bk-form
            ref="prodForm"
            :label-width="120"
            :model="formData"
            :rules="formRules"
            ext-cls="env-form-cls"
          >
            <bk-form-item
              :label="$t('资源配额方案')"
              :required="true"
              :property="'prod.plan_name'"
              :error-display-type="'normal'"
            >
              <bk-select
                v-model="formData.prod.plan_name"
                style="width: 300px"
                ext-cls="plan-select-cls"
                @change="(value) => handlePlanChange(value, 'prod')"
              >
                <bk-option
                  v-for="option in planList"
                  :key="option.value"
                  :id="option.value"
                  :name="option.name"
                ></bk-option>
              </bk-select>
            </bk-form-item>
            <div class="c-form-item-row flex-row align-items-center gap-16">
              <bk-form-item
                label="CPU"
                :required="true"
                :property="'prod.resources.limits.cpu'"
                :error-display-type="'normal'"
              >
                <div class="flex-row align-items-center gap-16">
                  <PrefixSelect
                    v-model="formData.prod.resources.limits.cpu"
                    prefix="Limit"
                    :options="cpuList"
                    :disabled="!isProdCustom"
                  />
                </div>
              </bk-form-item>
              <bk-form-item
                label=""
                :required="true"
                :property="'prod.resources.requests.cpu'"
                :error-display-type="'normal'"
              >
                <div class="flex-row align-items-center gap-16">
                  <PrefixSelect
                    v-model="formData.prod.resources.requests.cpu"
                    prefix="Request"
                    :options="cpuList"
                    :disabled="!isProdCustom"
                  />
                </div>
              </bk-form-item>
            </div>
            <div class="c-form-item-row flex-row align-items-center gap-16">
              <bk-form-item
                :label="$t('内存')"
                :required="true"
                :property="'prod.resources.limits.memory'"
                :error-display-type="'normal'"
              >
                <div class="flex-row align-items-center gap-16">
                  <PrefixSelect
                    v-model="formData.prod.resources.limits.memory"
                    prefix="Limit"
                    :options="memoryList"
                    :disabled="!isProdCustom"
                  />
                </div>
              </bk-form-item>
              <bk-form-item
                label=""
                :required="true"
                :property="'prod.resources.requests.memory'"
                :error-display-type="'normal'"
              >
                <div class="flex-row align-items-center gap-16">
                  <PrefixSelect
                    v-model="formData.prod.resources.requests.memory"
                    prefix="Request"
                    :options="memoryList"
                    :disabled="!isProdCustom"
                  />
                </div>
              </bk-form-item>
            </div>
          </bk-form>
        </div>
      </div>
      <div class="mt-24">
        <bk-button
          :theme="'primary'"
          @click="handleSubmit"
        >
          {{ $t('保存') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          type="submit"
          class="ml-8"
          @click="handleCancel"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </section>
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import PrefixSelect from './comps/prefix-select.vue';

export default {
  name: 'ResourceQuota',
  props: {
    moduleId: {
      type: String,
      default: '',
    },
    processData: {
      type: Object,
      default: () => {},
    },
  },
  components: {
    DetailsRow,
    PrefixSelect,
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

    // 创建空的 resources 结构
    const createEmptyResources = () => ({
      limits: {
        cpu: '',
        memory: '',
      },
      requests: {
        cpu: '',
        memory: '',
      },
    });

    return {
      formData: {
        stag: {
          plan_name: '',
          resources: createEmptyResources(),
        },
        prod: {
          plan_name: '',
          resources: createEmptyResources(),
        },
      },
      // 资源配额方案
      planList: [],
      cpuList: [],
      memoryList: [],
      // 表单校验规则
      formRules: {
        'stag.plan_name': requiredRule,
        'stag.resources.limits.cpu': requiredRule,
        'stag.resources.requests.cpu': requiredRule,
        'stag.resources.limits.memory': requiredRule,
        'stag.resources.requests.memory': requiredRule,
        'prod.plan_name': requiredRule,
        'prod.resources.limits.cpu': requiredRule,
        'prod.resources.requests.cpu': requiredRule,
        'prod.resources.limits.memory': requiredRule,
        'prod.resources.requests.memory': requiredRule,
      },
      isEdit: false,
      // 备份原始数据
      originalFormData: null,
    };
  },
  computed: {
    appCode() {
      return this.$route.params.code;
    },
    isStagCustom() {
      return this.formData.stag.plan_name === 'custom';
    },
    isProdCustom() {
      return this.formData.prod.plan_name === 'custom';
    },
    // 环境列表
    envList() {
      return [
        { key: 'stag', label: this.$t('预发布环境') },
        { key: 'prod', label: this.$t('生产环境') },
      ];
    },
  },
  watch: {
    processData: {
      handler() {
        this.initFormData();
      },
      deep: true,
      immediate: true,
    },
  },
  created() {
    this.init();
  },
  methods: {
    // 获取资源配额方案名称
    getPlanName(env) {
      if (this.formData[env].plan_name === 'custom') {
        return this.$t('自定义');
      }
      const plan = this.planList.find((item) => item.value === this.formData[env].plan_name);
      return plan?.name || this.formData[env].plan_name || '--';
    },
    // 创建空的 resources 结构
    createEmptyResources() {
      return {
        limits: {
          cpu: '',
          memory: '',
        },
        requests: {
          cpu: '',
          memory: '',
        },
      };
    },
    // 初始化
    async init() {
      await this.fetchPlanList();
      await this.fetchQuantityOptions();
      // 初始化数据
      this.initFormData();
    },
    // 初始化表单数据
    initFormData() {
      if (!this.processData.env_overlays) return;

      const { prod, stag } = this.processData.env_overlays;
      [
        { env: 'stag', data: stag },
        { env: 'prod', data: prod },
      ].forEach(({ env, data }) => {
        if (!data) return;

        // resources 不为 null 且不为 undefined 表示自定义资源配额
        if (data.resources !== null && data.resources !== undefined) {
          // 自定义资源配额
          this.formData[env].plan_name = 'custom';
          this.formData[env].resources = {
            limits: data.resources.limits || { cpu: '', memory: '' },
            requests: data.resources.requests || { cpu: '', memory: '' },
          };
        } else if (data.plan_name) {
          // 预设方案（resources 为 null）
          this.formData[env].plan_name = data.plan_name;
          this.handlePlanChange(data.plan_name, env);
        }
      });
    },
    handleEdit() {
      // 备份当前数据
      this.originalFormData = JSON.parse(JSON.stringify(this.formData));
      this.isEdit = true;
    },
    // 取消编辑
    handleCancel() {
      if (this.originalFormData) {
        // 还原备份的数据
        this.formData = JSON.parse(JSON.stringify(this.originalFormData));
        this.originalFormData = null;
      }
      this.isEdit = false;
    },
    // 获取资源配额方案
    async fetchPlanList() {
      try {
        const res = await this.$store.dispatch('deploy/fetchQuotaPlans', {});
        this.planList = res;
        this.planList.push({ name: this.$t('自定义'), value: 'custom' });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 获取资源配额选项
    async fetchQuantityOptions() {
      try {
        const res = await this.$store.dispatch('tenantOperations/fetchQuantityOptions');
        this.cpuList = res.cpu_resource_quantity;
        this.memoryList = res.memory_resource_quantity;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 处理资源配额方案切换
    handlePlanChange(value, env) {
      if (!value || value === '') {
        // 清空选项，重置数据
        this.formData[env].plan_name = '';
        this.formData[env].resources = this.createEmptyResources();
      } else if (value === 'custom') {
        // 自定义，用户自行选择
        this.formData[env].plan_name = 'custom';
        this.formData[env].resources = this.createEmptyResources();
      } else {
        // 预设方案，填充预设值
        const plan = this.planList.find((item) => item.value === value);
        if (plan) {
          this.formData[env].plan_name = value;
          this.formData[env].resources = {
            limits: plan.limit || { cpu: '', memory: '' },
            requests: plan.request || { cpu: '', memory: '' },
          };
        } else {
          // 找不到方案，使用空值
          this.formData[env].plan_name = value;
          this.formData[env].resources = this.createEmptyResources();
        }
      }
    },
    // 提交
    async handleSubmit() {
      try {
        // 并行校验两个表单
        await Promise.all([this.$refs.stagForm.validate(), this.$refs.prodForm.validate()]);
        // 校验通过，提交数据
        await this.updateProcessResources();
      } catch (error) {
        console.log('Form validation failed', error);
      }
    },
    // 更新单个进程的资源限制
    async updateProcessResources() {
      // 构建接口数据格式
      const envOverlays = {};

      ['stag', 'prod'].forEach((env) => {
        const envData = this.formData[env];
        if (envData.plan_name === 'custom' || envData.plan_name === null) {
          // 自定义方案：plan_name 为 null，resources 有值
          envOverlays[env] = {
            plan_name: null,
            resources: envData.resources,
          };
        } else {
          // 预设方案：plan_name 有值，resources 为 null
          envOverlays[env] = {
            plan_name: envData.plan_name,
            resources: null,
          };
        }
      });

      try {
        await this.$store.dispatch('tenantOperations/updateProcessQuantity', {
          appCode: this.appCode,
          moduleId: this.moduleId,
          processName: this.processData.name,
          data: {
            env_overlays: envOverlays,
          },
        });
        this.$emit('update', false);
        this.$bkMessage({
          theme: 'success',
          message: this.$t('保存成功'),
        });
        // 保存成功后清空备份并关闭编辑模式
        this.originalFormData = null;
        this.isEdit = false;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.resource-quota-container {
  padding: 24px 0;
  .top-section {
    height: 32px;
    .title {
      width: 104px;
      padding-right: 24px;
      text-align: right;
    }
  }
  .view-mode-section,
  .edit-mode-section {
    margin-left: 104px;
    margin-top: 16px;
  }
  .env-container {
    flex: 1;
    margin-right: 104px;
    .plan-select-cls {
      background-color: #fff;
    }
    .env-name {
      height: 32px;
      line-height: 32px;
      padding: 0 16px;
      color: #313238;
      background-color: #f0f1f5;
    }
    .env-form {
      padding: 24px;
      background-color: #f5f7fa;
      /deep/ .bk-form-item.is-error .PrefixSelect-cls {
        position: relative;
        z-index: 99;
      }
      /deep/ .details-row .value {
        padding-left: 10px;
      }
    }
    .c-form-item-row {
      margin-top: 22px;
      /deep/ .bk-form-item {
        margin-top: 0;
        &:last-child .bk-form-content {
          margin-left: 0 !important;
        }
      }
    }
  }
}
</style>
