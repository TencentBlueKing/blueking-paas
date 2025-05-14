<template>
  <div class="code-quality">
    <div class="title">{{ $t('数据概览') }}</div>
    <ul class="quality-info">
      <li
        class="item"
        v-for="item in pageInfo"
        :key="item.label"
      >
        <p class="count">{{ item.value }}</p>
        <p class="label">
          {{ item.label }}
          <i
            v-if="item.tips"
            v-bk-tooltips="item.tips"
            class="paasng-icon paasng-info-line ml5"
          />
        </p>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'PluginCodeScoring',
  props: {
    viewInfo: {
      type: Object,
      default: () => {},
    },
  },
  computed: {
    pageInfo() {
      const codeCheckInfo = this.viewInfo.codeCheckInfo || {};
      const qualityInfo = this.viewInfo.qualityInfo || {};
      return [
        {
          label: this.$t('代码质量'),
          value: codeCheckInfo.repoCodeccAvgScore ?? '--',
          tips: this.$t('质量评价依照腾讯开源治理指标体系 (其中文档质量暂按100分计算)， 评分仅供参考。'),
        },
        {
          label: this.$t('已解决缺陷数'),
          value: codeCheckInfo.resolvedDefectNum ?? '--',
        },
        {
          label: this.$t('质量红线拦截率'),
          value: qualityInfo.qualityInterceptionRate ?? '--',
          tips: `${this.$t('拦截次数:')} ${qualityInfo.interceptionCount ?? '--'} / ${this.$t('运行总次数:')} ${
            qualityInfo.totalExecuteCount ?? '--'
          }`,
        },
      ];
    },
  },
};
</script>

<style lang="scss" scoped>
.code-quality {
  margin-top: 32px;
  .title {
    margin-bottom: 8px;
    font-weight: 700;
    font-size: 14px;
    color: #313238;
  }
  .quality-info {
    .item {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 74px;
      background: #f5f7fa;
      border-radius: 2px;
      margin-bottom: 12px;
      &:last-child {
        margin-bottom: 0;
      }
    }
    .count {
      font-size: 24px;
      color: #313238;
    }
    .label {
      position: relative;
      font-size: 12px;
      color: #4d4f56;
      line-height: 20px;
      .paasng-info-line {
        position: absolute;
        right: -18px;
        top: 50%;
        transform: translateY(-50%);
        color: #c4c6cc;
      }
    }
  }
}
</style>
