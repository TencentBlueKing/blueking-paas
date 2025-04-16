<template>
  <div class="sensitive-text-wrapper">
    <span v-if="!text">--</span>
    <template v-else>
      <span v-if="!showText">**********</span>
      <span v-else>{{ text }}</span>
      <span class="icon-wrapper">
        <i
          :class="['paasng-icon', showText ? 'paasng-eye' : 'paasng-eye-slash']"
          @click="toggleShow"
          v-bk-tooltips="showText ? $t('隐藏') : $t('显示')"
        ></i>
        <i
          v-if="copyable"
          class="paasng-icon paasng-general-copy"
          v-copy="text"
          v-bk-tooltips="$t('复制')"
        ></i>
      </span>
    </template>
  </div>
</template>

<script>
export default {
  name: 'SensitiveText',
  props: {
    // 敏感文本内容
    text: {
      type: [String, Number],
      default: '',
    },
    // 是否默认显示文本
    defaultValue: {
      type: Boolean,
      default: false,
    },
    // 是否显示复制按钮
    copyable: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      showText: this.defaultValue,
    };
  },
  methods: {
    toggleShow() {
      this.showText = !this.showText;
      this.$emit('toggle', this.showText);
    },
  },
};
</script>

<style scoped>
.sensitive-text-wrapper {
  display: inline-flex;
  align-items: center;
}

.icon-wrapper {
  margin-left: 8px;
  display: inline-flex;
  gap: 6px;
}

.paasng-icon {
  cursor: pointer;
  font-size: 14px;
}

.paasng-icon:hover {
  color: #3a84ff;
}
</style>
