<template>
  <div>
    <bk-sideslider
      :is-show.sync="sidesliderVisible"
      :quick-close="true"
      width="960"
      :title="title"
      @shown="handleShown"
    >
      <div
        class="sideslider-content"
        slot="content"
      >
        <div
          class="markdown-body"
          v-dompurify-html="markdownContent"
        />
        <app-description :doc="doc" />
      </div>
    </bk-sideslider>
  </div>
</template>

<script>
import MarkdownIt from 'markdown-it';
import appDescription from './app-description.vue';
export default {
  components: { appDescription },
  name: 'GuideSideslider',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    title: {
      type: String,
      default: '',
    },
    md: {
      type: String,
      default: '',
    },
    doc: {
      type: String,
      default: 'svc-discovery.md',
    },
  },
  data() {
    return {
      markdownContent: '',
    };
  },
  computed: {
    sidesliderVisible: {
      get: function () {
        return this.show;
      },
      set: function (val) {
        this.$emit('update:show', val);
      },
    },
    appCode() {
      return this.$route.params.id;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  methods: {
    handleShown() {
      this.loadMarkdownFile();
    },
    loadMarkdownFile() {
      const md = new MarkdownIt();
      let markdownContent = '';
      // 引入md文件/区分语言环境
      markdownContent =
        this.localLanguage === 'en'
          ? require(`!!raw-loader!@/assets/md/en/${this.md}`).default
          : require(`!!raw-loader!@/assets/md/${this.md}`).default;
      const htmlStr = md.render(markdownContent);
      // 替换a标签属性，使用新标签页打开
      this.markdownContent = htmlStr.replace(/<a/g, '<a target="_blank"');
      const docLinkList = ['PROCFILE_DOC', 'BUILD_PHASE_HOOK', 'DEPLOY_ORDER', 'APP_DESC_DOC'];
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
.sideslider-content {
  padding: 24px;
  .guide-alert-content {
    p {
      line-height: 20px;
    }
  }
}
.markdown-body {
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
