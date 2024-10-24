<template>
  <div class="record-diff-container">
    <!-- top -->
    <div class="top-title">
      <div class="left item">
        <span>{{ $t('操作前') }}</span>
      </div>
      <div class="right item">
        <span>{{ $t('操作后') }}</span>
      </div>
    </div>
    <bk-diff
      :old-content="oldCode"
      :new-content="newCode"
      :language="language"
      :format="'side-by-side'"
      theme="dark"
      ext-cls="record-diff-cls"
    ></bk-diff>
    <section class="buttom-status-bar">
      <div
        class="item"
        v-for="item in statusMap"
        :key="item.name"
      >
        <div
          class="blocks"
          :style="{ background: item.color[0] }"
        ></div>
        <div
          class="blocks"
          :style="{ background: item.color[1], marginLeft: '1px' }"
        ></div>
        <span :style="{ color: item.color[2] }">{{ item.name }}</span>
      </div>
    </section>
  </div>
</template>

<script>
export default {
  name: 'RecordDiff',
  props: {
    oldCode: {
      type: String,
      default: '',
    },
    newCode: {
      type: String,
      default: '',
    },
    language: {
      type: String,
      default: 'javascript',
    },
  },
  data() {
    return {
      statusMap: [
        {
          name: this.$t('删除'),
          color: ['#702622', '#666666', '#EA3636'],
        },
        {
          name: this.$t('变化'),
          color: ['#702622', '#3D4D1F', '#B6B6B6'],
        },
        {
          name: this.$t('新增'),
          color: ['#666666', '#3D4D1F', '#6E963C'],
        },
      ],
    };
  },
};
</script>

<style lang="scss" scoped>
.record-diff-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #1d1d1d;
  .top-title {
    flex: 0 0 auto; /* 固定高度，不伸缩 */
    height: 44px;
    display: flex;
    align-items: center;
    .item {
      flex: 1;
      height: 100%;
      line-height: 44px;
      padding-left: 16px;
      background: #2e2e2e;
      &.right {
        border-left: 1px solid #313238;
        span {
          color: #3fc362;
          background: #144628;
        }
      }
      span {
        display: inline-block;
        height: 22px;
        line-height: 22px;
        padding: 0 8px;
        color: #64a0fa;
        background: #1e3567;
        border-radius: 2px;
      }
    }
  }
  .record-diff-cls {
    flex: 1 1 auto;
    overflow: hidden;
    overflow-y: auto;
    &::-webkit-scrollbar {
      width: 6px;
      background-color: lighten(transparent, 80%);
    }
    &::-webkit-scrollbar-thumb {
      height: 5px;
      border-radius: 2px;
      background-color: #616161;
    }
    /deep/ .d2h-file-wrapper {
      border: none;
      .d2h-code-wrapper {
        border-left: none !important;
        tbody.d2h-diff-tbody tr {
          position: relative;
        }
      }
      .d2h-file-side-diff {
        border-left: 1px solid #313238;
        background: #1d1d1d;
        margin-bottom: 0;
        &::-webkit-scrollbar-thumb {
          background-color: #616161;
        }
      }
      .d2h-code-wrapper {
        .hljs {
          white-space: pre;
        }
        code,
        pre {
          font-family: Menlo, Monaco, Consolas, Courier, monospace;
        }
      }
    }
  }
  .buttom-status-bar {
    position: relative;
    z-index: 99;
    flex: 0 0 auto; /* 固定高度，不伸缩 */
    display: flex;
    align-items: center;
    height: 48px;
    padding-left: 16px;
    background: #2e2e2e;
    box-shadow: 0 -1px 0 0 #313238;
    .item {
      display: flex;
      align-items: center;
      margin-right: 20px;
      .blocks {
        width: 12px;
        height: 12px;
      }
      span {
        font-size: 12px;
        margin-left: 6px;
      }
    }
  }
}
</style>
