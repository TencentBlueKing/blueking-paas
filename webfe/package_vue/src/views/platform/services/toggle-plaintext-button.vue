<template>
  <bk-button
    text
    @click="handleToggle"
  >
    <i
      :class="['paasng-icon mr5', isAllPlaintext ? 'paasng-bukeyulan' : 'paasng-insights']"
      v-bk-tooltips="isAllPlaintext ? $t('隐藏配置') : $t('显示配置')"
    ></i>
    <span>{{ isAllPlaintext ? $t('隐藏配置') : $t('显示配置') }}</span>
  </bk-button>
</template>

<script>
export default {
  name: 'TogglePlaintextButton',
  props: {
    // 是否全部显示明文
    value: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    isAllPlaintext() {
      return this.value;
    },
  },
  methods: {
    handleToggle() {
      this.$emit('input', !this.value);
      this.$emit('toggle', !this.value);
    },
  },
};
</script>
