<template>
  <div class="market-info-container card-style">
    <p class="title">
      {{ $t('市场信息') }}
      <span
        class="market-edit"
        @click="toMarketInfo"
      >
        <i class="paasng-icon paasng-edit-2" />
        {{ $t('编辑') }}
      </span>
    </p>
    <p class="description">{{ $t('用于插件市场展示的信息') }}</p>
    <section class="main">
      <ul class="detail-wrapper">
        <li class="item-info">
          <div class="describe">
            {{ $t('应用分类') }}
          </div>
          <div class="content">{{ marketInfo.category || '--' }}</div>
        </li>
        <li class="item-info">
          <div class="describe">
            {{ $t('应用简介') }}
          </div>
          <div class="content">{{ marketInfo.introduction || '--' }}</div>
        </li>
        <li class="item-info">
          <div class="describe">
            {{ $t('应用联系人') }}
          </div>
          <div class="content">{{ marketInfo.contactArr?.length ? marketInfo.contactArr.join() : '--' }}</div>
        </li>
        <li class="item-info">
          <div class="describe">
            {{ $t('详情描述') }}
          </div>
          <div class="content description-content">
            <div
              :class="[
                'display-description',
                { 'description-ellipsis': hideBeyondArea },
                isExpanded ? 'unfold' : 'up',
              ]"
            >
              <div
                ref="editorRef"
                v-dompurify-html="marketInfo.description ? marketInfo.description : '--'"
              />
            </div>
            <span
              v-if="hideBeyondArea === 'down'"
              class="unfold-btn"
              @click="isExpanded = !isExpanded"
            >
              {{ isExpanded ? $t('收起') : $t('展开') }}
              <i :class="['paasng-icon', isExpanded ? 'paasng-angle-line-up' : 'paasng-angle-line-down']" />
            </span>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<script>
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
export default {
  mixins: [pluginBaseMixin],
  props: {
    marketInfo: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      hideBeyondArea: '',
      isExpanded: false,
    };
  },
  watch: {
    marketInfo: {
      handler() {
        this.handleExpandOperation();
      },
      immediate: true,
    },
  },
  mounted() {
    this.handleExpandOperation();
  },
  methods: {
    // 编辑页
    toMarketInfo() {
      this.$router.push({
        name: 'marketInfoEdit',
      });
    },
    handleExpandOperation() {
      this.$nextTick(() => {
        const elHeight = this.$refs.editorRef.offsetHeight;
        this.hideBeyondArea = elHeight > 200 ? 'down' : '';
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.market-info-container {
  padding: 24px;
  .title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
    .market-edit,
    .plugin-name-icon-cls {
      cursor: pointer;
      font-size: 14px;
      font-weight: 400;
      margin-left: 5px;
      color: #3a84ff;

      i {
        font-size: 16px;
        transform: translateX(2px);
      }
    }
  }
  .description {
    margin-top: 4px;
    margin-bottom: 8px;
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
  }

  .description-content {
    position: relative;
    font-size: 12px;
    padding: 10px 10px 30px 16px;
    .unfold {
      overflow: auto;
      min-height: 200px;
    }
    .up {
      height: 200px;
      overflow: hidden;
    }
    .is-down {
      transform-origin: 50% 50%;
    }
    .unfold-btn {
      position: absolute;
      bottom: 5px;
      right: 10px;
      cursor: pointer;
      color: #3a84ff;
      i {
        transform-origin: 50% 50%;
        transform: translateX(-2px);
      }
    }
  }

  .detail-wrapper {
    border: 1px solid #dcdee5;
    .item-info {
      display: flex;
      min-height: 42px;
      border-top: 1px solid #dcdee5;

      &:first-child {
        border-top: none;
      }
      .describe,
      .content {
        display: flex;
        align-items: center;
      }
      .describe {
        flex-shrink: 0;
        justify-content: center;
        width: 180px;
        text-align: right;
        font-size: 12px;
        color: #313238;
        line-height: normal;
        background: #fafbfd;
      }
      .content {
        flex-wrap: wrap;
        line-height: 1.5;
        word-break: break-all;
        flex: 1;
        font-size: 12px;
        color: #63656e;
        padding-left: 16px;
        border-left: 1px solid #dcdee5;
      }
    }
  }
}
</style>
