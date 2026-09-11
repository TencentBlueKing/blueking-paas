<template>
  <pre
    class="log-display"
    v-dompurify-html="content"
  />
</template>

<script>
export default {
  name: 'LogDisplay',
  props: {
    content: {
      type: String,
      default: '',
    },
  },
};
</script>

<style lang="scss" scoped>
.log-display {
  flex: 1;
  min-width: 0;
  min-height: 0;
  margin: 0;
  padding: 20px;
  overflow: auto;
  color: #fff;
  background: #2a2b2f;
  font-family: Consolas, 'Source Code Pro', 'Bitstream Vera Sans Mono', 'Courier New', monospace;

  &::-webkit-scrollbar {
    width: 4px;
    height: 4px;
    background-color: lighten(transparent, 80%);
  }

  &::-webkit-scrollbar-thumb {
    border-radius: 2px;
    background-color: #63656e;
  }
}
</style>
