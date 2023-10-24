<template>
  <bk-sideslider
    :is-show.sync="isShow"
    :title="name === 'hook' ? $t('钩子命令') : $t('进程配置')"
    :width="960"
    quick-close
  >
    <div slot="content">
      <div class="markdown-body">
        <guide-hook v-if="name === 'hook'" />
        <guide-process v-else />
      </div>
    </div>
  </bk-sideslider>
</template>

<script>
import guideHook from '@/assets/md/guide-hook.md';
import guideProcess from '@/assets/md/guide-process.md';
export default {
  components: { guideHook, guideProcess },
  props: {
    name: String,
  },
  data() {
    return {
      isShow: false,
    };
  },
  methods: {
    showSideslider() {
      this.isShow = true;
    },
  },
};
</script>

<style lang="scss" scoped>
.markdown-body section {
  padding: 24px;
  /deep/ {
    body,
    html {
      width: 100% !important;
      min-width: auto !important;
    }
    ol {
      list-style: decimal !important;
    }
  }
}
</style>
