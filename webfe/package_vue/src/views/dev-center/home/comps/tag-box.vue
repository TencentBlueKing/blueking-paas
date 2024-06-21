<template>
  <div
    class="box"
    ref="tagsRef"
  >
    <i class="paasng-icon paasng-user user-icon"></i>
    <div
      v-for="(tag, index) in visibleTags"
      :key="index"
      class="tag"
    >
      {{ tag }}
    </div>
    <div
      v-if="hiddenCount > 0"
      class="more"
      v-bk-tooltips="{ content: hiddenTags.join(', ') }"
    >
      +{{ hiddenCount }}
    </div>
  </div>
</template>

<script>
export default {
  props: {
    tags: {
      type: Array,
      required: true,
    },
  },
  data() {
    return {
      visibleTags: [],
      hiddenTags: [],
      hiddenCount: 0,
    };
  },
  watch: {
    tags: {
      immediate: true,
      handler() {
        this.$nextTick(() => {
          this.updateTags();
        });
      },
    },
  },
  mounted() {
    this.updateTags();
    window.addEventListener('resize', this.updateTags);
  },
  beforeDestroy() {
    window.removeEventListener('resize', this.updateTags);
  },
  methods: {
    updateTags() {
      const box = this.$refs.tagsRef;
      const tempDiv = document.createElement('div');
      tempDiv.style.position = 'absolute';
      tempDiv.style.visibility = 'hidden';
      tempDiv.style.whiteSpace = 'nowrap';
      document.body.appendChild(tempDiv);

      let totalWidth = 0;
      const reservedWidth = 140; // 预留值
      const marginRight = 4;
      this.visibleTags = [];
      this.hiddenTags = [];
      this.hiddenCount = 0;

      this.tags.forEach((tag) => {
        tempDiv.textContent = tag;
        tempDiv.className = 'tag';
        const tagWidth = tempDiv.offsetWidth + marginRight;

        // 包括 more 标签占用的宽度进行判断
        if (totalWidth + tagWidth + reservedWidth <= box?.clientWidth) {
          this.visibleTags.push(tag);
          totalWidth += tagWidth;
        } else {
          this.hiddenTags.push(tag);
          this.hiddenCount += 1;
        }
      });
      document.body.removeChild(tempDiv);
    },
  },
};
</script>

<style lang="scss" scoped>
.box {
  width: 100%;
  white-space: nowrap;
  overflow: hidden;
  position: relative;
  box-sizing: border-box;
}
.tag,
.more {
  display: inline-block;
  margin-right: 4px;
  padding: 4px 8px;
  background: #fafbfd;
  border-radius: 2px;
  white-space: nowrap;
}
.more {
  &:hover {
    background: #dcdee5;
  }
}
.user-icon {
  font-size: 16px;
  color: #979BA5;
  margin-right: 6px;
  transform: translateY(1px);
}
</style>
