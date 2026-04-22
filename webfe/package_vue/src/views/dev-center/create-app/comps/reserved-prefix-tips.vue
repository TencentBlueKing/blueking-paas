<template>
  <div
    v-if="matchedPrefixes.length"
    class="reserved-prefix-tips"
  >
    <bk-alert
      type="warning"
      ext-cls="alert-tip-cls"
    >
      <div slot="title">
        {{ $t('使用 {n} 前缀的应用 ID 需要输入授权码才能创建', { n: matchedPrefixes.join('、') }) }}
        <a
          class="ml5"
          target="_blank"
        >
          {{ $t('查看申请指引') }}
          <i class="paasng-icon paasng-jump-link"></i>
        </a>
      </div>
    </bk-alert>
    <bk-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      class="mt-10"
      form-type="vertical"
    >
      <bk-form-item
        property="authCode"
        :required="true"
        :label="$t('授权码')"
        :error-display-type="'normal'"
      >
        <bk-input
          v-model="formData.authCode"
          :placeholder="$t('请输入该 ID 对应的 8 位授权码')"
        />
      </bk-form-item>
    </bk-form>
  </div>
</template>

<script>
export default {
  props: {
    code: {
      type: String,
      default: '',
    },
    reservedPrefixes: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      formData: {
        authCode: '',
      },
      rules: {
        authCode: [
          {
            required: true,
            message: this.$t('必填项'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  computed: {
    matchedPrefixes() {
      if (!this.code || !this.reservedPrefixes.length) return [];
      return this.reservedPrefixes.filter((prefix) => this.code.startsWith(prefix));
    },
  },
  methods: {
    /**
     * 校验授权码是否已填写
     */
    async validate() {
      await this.$refs.formRef?.validate();
    },
    /**
     * 获取授权码值
     * @returns {string} 授权码
     */
    getCode() {
      return this.formData.authCode;
    },
  },
};
</script>

<style lang="scss" scoped>
.reserved-prefix-tips {
  margin-top: 12px;
  padding: 16px 24px;
  background-color: #f5f7fa;
  .alert-tip-cls {
    /deep/ .paasng-remind {
      align-items: flex-start;
    }
  }
}
</style>
