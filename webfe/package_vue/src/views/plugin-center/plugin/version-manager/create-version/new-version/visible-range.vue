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
            <div class="value organization" v-if="organizationLevel.length">
              <p v-for="item in organizationLevel" :key="item.id">
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
import { buildPath } from '@/common/tools';

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
  data() {
    return {
      // 缓存池
      cachePool: new Map(),
      organizationLevel: [],
    };
  },
  watch: {
    'data.organization'(newValue) {
      this.requestAllOrganization(newValue);
    },
  },
  methods: {
    // 请求组织的层级结构
    async requestAllOrganization(data) {
      if (!data.length) return;

      // 过滤出需要请求的新数据
      const newData = data.filter(item => !this.cachePool.has(item.id));

      // 对新数据发送请求
      const requests = newData.map(item => this.$store.dispatch('plugin/getOrganizationLevel', { id: item.id }));
      const res = await Promise.all(requests);

      // 处理返回的数据
      res.forEach((item, index) => {
        const name = buildPath(item);
        const { id } = newData[index];  // 对应的 id
        this.cachePool.set(id, { name, id });  // 缓存处理后的结果
      });

      this.organizationLevel = data.map(item => this.cachePool.get(item.id));
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
