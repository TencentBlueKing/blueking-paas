<template>
  <bk-sideslider
    :is-show.sync="isShow"
    :title="name === 'hook' ? $t('钩子命令') : $t('进程配置')"
    :width="960"
    quick-close
  >
    <div slot="content">
      <bk-tab
        :active.sync="active"
        type="unborder-card"
        ext-cls="guide-tab-cls"
        @tab-change="handleChange">
        <bk-tab-panel
          v-for="(panel, index) in panels"
          v-bind="panel"
          :key="index"
        >
        </bk-tab-panel>
      </bk-tab>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div class="markdown-body" v-html="markdownContent" />
    </div>
  </bk-sideslider>
</template>

<script>
import MarkdownIt from 'markdown-it';
export default {
  data() {
    return {
      isShow: false,
      markdownContent: '',
      active: 'procss',
      panels: [
        { name: 'procss', label: this.$t('进程配置') },
        { name: 'hook', label: this.$t('钩子命令') },
      ],
    };
  },
  methods: {
    showSideslider() {
      this.isShow = true;
      this.loadMarkdownFile();
    },
    handleChange(name) {
      this.active = name;
      this.loadMarkdownFile();
    },
    loadMarkdownFile() {
      const md = new MarkdownIt();
      let markdownContent = '';
      // 引入md文件
      if (this.active === 'hook') {
        markdownContent = require('!!raw-loader!@/assets/md/guide-hook.md').default;
      } else {
        markdownContent = require('!!raw-loader!@/assets/md/guide-process.md').default;
      }
      const htmlStr = md.render(markdownContent);
      // 替换a标签属性，使用新标签页打开
      this.markdownContent = htmlStr.replace(/<a/g, '<a target="_blank"');
    },
  },
};
</script>

<style lang="scss" scoped>
.markdown-body {
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
.guide-tab-cls {
  padding: 0 24px;
}
</style>
