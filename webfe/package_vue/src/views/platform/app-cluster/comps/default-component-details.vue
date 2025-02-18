<template>
  <div class="default-component-details">
    <!-- 默认组件详情样式 -->
    <DetailsRow
      :label-width="80"
      :label="`${$t('组件介绍')}：`"
      value="--"
    />
    <DetailsRow
      :label-width="80"
      :is-full="true"
      :align="'flex-start'"
    >
      <template slot="label">{{ `${$t('组件配置')}：` }}</template>
      <div slot="value">
        {{ $t('使用默认 values 部署即可。') }}
        <!-- <bk-button
          :text="true"
          size="small"
          @click="handleViewValues"
        >
          <i class="paasng-icon paasng-process-file"></i>
          <span>{{ $t('查看 Values') }}</span>
        </bk-button> -->
      </div>
    </DetailsRow>
    <DetailsRow
      :label-width="80"
      :is-full="true"
      :align="'flex-start'"
    >
      <template slot="label">{{ `${$t('组件状态')}：` }}</template>
      <div slot="value">
        {{ COMPONENT_STATUS[data?.status] || '--' }}
        <bk-button
          v-if="data?.status === 'installed'"
          :text="true"
          size="small"
          @click="handleViewDetail"
        >
          <i class="paasng-icon paasng-process-file"></i>
          <span>{{ $t('查看详情') }}</span>
        </bk-button>
      </div>
    </DetailsRow>
    <DetailComponentsSideslider
      :show.sync="isShowDetail"
      :name="data?.name"
      v-bind="$attrs"
    />
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
import DetailComponentsSideslider from './detail-components-sideslider.vue';
import { COMPONENT_STATUS } from '@/common/constants';
export default {
  name: 'DefaultComponentDetails',
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
  components: {
    DetailsRow,
    DetailComponentsSideslider,
  },
  data() {
    return {
      COMPONENT_STATUS,
      isShowDetail: false,
    };
  },
  methods: {
    handleViewDetail() {
      this.isShowDetail = true;
    },
  },
};
</script>

<style lang="scss" scoped>
.default-component-details {
  .paasng-process-file {
    font-size: 14px;
    margin-right: 3px;
  }
}
</style>
