<template>
  <div class="paas-docu-wrapper">
    <section v-for="(item, index) in data" :key="index" class="docu-item">
      <p class="name" @click.stop="handleOpen(item)">
        <span v-dompurify-html="handleHighlight(item.title)" />
      </p>
      <div
        v-if="isShowContent(item.digest)"
        class="digest-content"
        @click.stop="handleOpen(item)"
        v-dompurify-html="handleContentHighlight(item.digest)"
      />
    </section>
  </div>
</template>
<script>
export default {
  name: '',
  props: {
    data: {
      type: Array,
      default: () => [],
    },
    filterKey: {
      type: [String, Number],
      default: '',
    },
  },
  computed: {
    isShowContent() {
      return (payload) => {
        if (typeof payload === 'number') {
          return true;
        }
        return !!payload;
      };
    },
  },
  methods: {
    // 安全的正则表达式转义函数
    escapeRegExp(string) {
      return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    },

    handleOpen({ url }) {
      window.open(url);
    },

    handleHighlight(payload) {
      if (this.filterKey === '') {
        return payload;
      }
      let keyword = this.filterKey.trim();
      keyword = `(${this.escapeRegExp(keyword)})`;
      const patt = new RegExp(keyword, 'igm');
      return payload.replace(patt, '<span class="keyword">$1</span>');
    },

    handleContentHighlight(payload) {
      const highlightKey = 'bk-highlight-mark';
      const highlightPatt = new RegExp(highlightKey, 'igm');
      const content = payload.replace(highlightPatt, 'marked');
      if (this.filterKey === '') {
        return content;
      }
      let keyword = this.filterKey.trim();
      keyword = `(${this.escapeRegExp(keyword)})`;
      const patt = new RegExp(keyword, 'igm');
      return content.replace(patt, '<span class="keyword">$1</span>');
    },
  },
};
</script>
<style lang="scss">
.paas-docu-wrapper {
  padding-right: 320px;
  .docu-item {
    padding: 18px 0 20px 0;
    min-height: 64px;
    border-bottom: 1px solid #dcdee5;
    .name {
      display: inline-block;
      font-size: 18px;
      color: #313238;
      cursor: pointer;
      &:hover {
        color: #3a84ff;
        .keyword {
          color: #ff9c01;
        }
      }
      .keyword {
        padding: 0 3px;
        color: #ff9c01;
      }
    }
    .digest-content {
      margin-top: 10px;
      line-height: 24px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: normal;
      word-break: break-all;
      display: -webkit-box;
      -webkit-line-clamp: 1;
      -webkit-box-orient: vertical;
      color: #63656e;
      cursor: pointer;
      .keyword {
        padding: 0 3px;
        color: #ff9c01;
      }
      marked {
        color: #ff9c01 !important;
        span {
          color: #ff9c01 !important;
        }
      }
      &:hover {
        color: #3a84ff;
      }
    }
  }
}
</style>
