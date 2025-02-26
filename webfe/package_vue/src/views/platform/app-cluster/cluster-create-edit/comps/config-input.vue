<template>
  <div class="config-input-container">
    <bk-input
      :value="$attrs.value"
      @input="$emit('input', $event)"
      :type="type === 'input' ? undefined : type"
      v-bind="$attrs"
      :password-icon="[]"
      show-word-limit
    ></bk-input>
  </div>
</template>

<script>
export default {
  name: 'ConfigInputContainer',
  props: {
    type: {
      default: '',
    },
  },
  data() {
    return {};
  },
};
</script>

<style lang="scss" scoped></style>
