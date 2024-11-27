<template>
  <div class="risk">
    <bk-alert
      type="error"
      :show-icon="false"
      class="risk-alert-cls"
    >
      <div
        slot="title"
        class="risk-alert"
      >
        <i class="paasng-icon paasng-paas-remind-fill" />
        {{ $t('当前值由应用描述文件定义，继续编辑可能导致数据冲突，并存在被描述文件覆盖的风险。') }}
      </div>
    </bk-alert>
    <bk-checkbox
      :value="value"
      @input="updateValue"
      ext-cls="risk-confirmation"
    >
      {{ $t('我已知晓风险') }}
    </bk-checkbox>
  </div>
</template>

<script>
export default {
  props: {
    value: {
      type: Boolean,
      default: false,
    },
    doc: {
      type: String,
      default: '',
    },
  },
  methods: {
    updateValue(newValue) {
      this.$emit('input', newValue);
    },
  },
};
</script>

<style lang="scss" scoped>
.risk {
  margin-bottom: 16px;
  .risk-alert-cls {
    margin: 10px 0;
  }
}
.risk-alert {
  i {
    color: #ea3636;
    margin-right: 8px;
    font-size: 16px;
    transform: translateY(0);
  }
}
</style>
