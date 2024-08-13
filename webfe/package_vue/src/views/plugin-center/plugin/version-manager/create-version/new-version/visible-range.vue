<template>
  <div class="release-visible-range-container">
    <card
      class="mt16"
      :title="$t('可见范围')"
      :is-collapse="true"
    >
      <!-- 默认为只读 -->
      <view-mode>
        <ul class="visible-range-cls">
          <li class="item">
            <div class="label">{{ $t('蓝盾项目') }}：</div>
            <div class="value">{{ data.bkci_project.length ? data.bkci_project.join(',') : '--' }}</div>
          </li>
          <li class="item">
            <div class="label">{{ $t('组织') }}：</div>
            <div class="value organization" v-if="data.organization.length">
              <p v-for="item in data.organization" :key="item.id">
                {{ item.name }}
              </p>
            </div>
            <div class="value" v-else>--</div>
          </li>
        </ul>
      </view-mode>
    </card>
  </div>
</template>

<script>
import card from '@/components/card/card.vue';
import viewMode from './view-mode.vue';

export default {
  name: 'ReleaseVisibleRange',
  components: {
    card,
    viewMode,
  },
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
};
</script>

<style lang="scss" scoped>
.release-visible-range-container {
  .mt16 {
    margin-top: 16px;
  }
  .visible-range-cls {
    .organization {
      min-width: 323px;
      padding: 12px 16px;
      background: #F5F7FA;
      border-radius: 2px;
      color: #313238;
    }
  }
}
</style>
