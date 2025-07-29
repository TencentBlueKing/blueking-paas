<template>
  <bk-sideslider
    :is-show.sync="isShow"
    :title="active === 'hook' ? $t('钩子命令') : $t('进程配置')"
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
      <div class="markdown-body" v-dompurify-html="markdownContent" />
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
  computed: {
    localLanguage() {
      return this.$store.state.localLanguage;
    },
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
      // 引入md文件/区分语言环境
      if (this.active === 'hook') {
        markdownContent = this.localLanguage === 'en' ? require('!!raw-loader!@/assets/md/en/guide-hook.md').default : require('!!raw-loader!@/assets/md/guide-hook.md').default;
      } else {
        markdownContent = this.localLanguage === 'en' ? require('!!raw-loader!@/assets/md/en/guide-process.md').default : require('!!raw-loader!@/assets/md/guide-process.md').default;
      }
      const htmlStr = md.render(markdownContent);
      // 替换a标签属性，使用新标签页打开
      this.markdownContent = htmlStr.replace(/<a/g, '<a target="_blank"');
      const docLinkList = ['PROCFILE_DOC', 'BUILD_PHASE_HOOK', 'DEPLOY_ORDER', 'APP_DESC_CNATIVE'];
      // 替换环境变量
      this.markdownContent = htmlStr.replace(/<a href="([^"]*)"/g, (match, href) => {
        if (docLinkList.includes(href)) {
          return `<a href="${this.GLOBAL.DOC[href]}" target="_blank"`;
        }
        return match;
      });
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
