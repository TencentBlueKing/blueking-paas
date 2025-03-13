<template>
  <div class="detail-feature-container">
    <bk-button
      class="clustertab-edit-btn-cls"
      theme="primary"
      :outline="true"
      @click="handleEdit"
    >
      {{ $t('编辑') }}
    </bk-button>
    <div class="detail-title">{{ $t('集群特性') }}</div>
    <div class="header">
      <div class="label">{{ $t('集群特性') }}</div>
      <div class="value">{{ $t('是否启用') }}</div>
    </div>
    <ul class="feature">
      <li
        class="item"
        v-for="(item, index) in featureMaps"
        :key="index"
      >
        <div
          class="label"
          v-bk-overflow-tips
        >
          {{ item.name }}
        </div>
        <div class="value">
          <i
            class="paasng-icon paasng-correct"
            v-if="data.feature_flags?.[item.key]"
          ></i>
          <i
            class="paasng-icon paasng-icon-close"
            v-else
          ></i>
        </div>
      </li>
    </ul>
    <div class="detail-title">{{ $t('高级设置') }}</div>
    <DetailsRow
      :label-width="168"
      :is-full="true"
      :align="'flex-start'"
    >
      <template slot="label">{{ `${$t('节点选择器（nodeSelector）')}：` }}</template>
      <div
        slot="value"
        class="node-selector"
      >
        <template v-if="!data.node_selector || Object.keys(data.node_selector).length === 0">--</template>
        <span
          v-else
          v-for="(val, key) in data.node_selector"
          class="tag"
          :key="key"
        >
          {{ key }} = {{ val }}
        </span>
      </div>
    </DetailsRow>
    <DetailsRow
      :label-width="168"
      :is-full="true"
      :align="'flex-start'"
    >
      <template slot="label">{{ `${$t('容忍度（tolerations）')}：` }}</template>
      <div
        slot="value"
        class="toleration"
      >
        <template v-if="!data.tolerations || Object.keys(data.tolerations).length === 0">--</template>
        <div
          v-else
          v-for="(item, index) in data.tolerations"
          :key="index"
          class="row"
        >
          <div
            v-for="(v, k) in item"
            :class="['tag', k]"
            :key="k"
          >
            {{ v }}
          </div>
        </div>
      </div>
    </DetailsRow>
  </div>
</template>

<script>
import DetailsRow from '@/components/details-row';
export default {
  name: 'DetailFeature',
  components: {
    DetailsRow,
  },
  props: {
    data: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      featureMaps: [],
    };
  },
  created() {
    this.getClusterFeatureFlags();
  },
  methods: {
    async getClusterFeatureFlags() {
      try {
        const res = await this.$store.dispatch('tenant/getClusterFeatureFlags');
        this.featureMaps = res;
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    handleEdit() {
      this.$router.push({
        name: 'clusterCreateEdit',
        params: {
          type: 'edit',
        },
        query: {
          id: this.data.name,
          step: 4,
          alone: true,
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.detail-feature-container {
  position: relative;
  .detail-title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
    margin: 24px 0 12px 0;
    &:first-of-type {
      margin-top: 0;
    }
  }
  .header,
  .feature .item {
    width: 480px;
    display: flex;
    align-items: center;
    height: 32px;
    line-height: 32px;
    font-size: 12px;
    color: #313238;
    .label {
      width: 280px;
      padding-left: 16px;
      flex-shrink: 0;
      white-space: nowrap;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .value {
      flex: 1;
      i {
        transform: translateX(-5px);
        font-size: 24px;
        &.paasng-correct {
          color: #2caf5e;
        }
        &.paasng-icon-close {
          color: #979ba5;
        }
      }
    }
  }
  .header {
    height: 33px;
    line-height: 33px;
    color: #313238;
    background: #f5f7fa;
    border-bottom: 1px solid #dcdee5;
  }
  .feature {
    li.item:nth-child(even) {
      background: #fafbfd;
    }
  }
  .node-selector .tag {
    margin-right: 4px;
  }
  .toleration {
    margin-top: 5px;
    .row {
      display: flex;
      align-items: center;
      margin-bottom: 4px;
      .key {
        position: static;
      }
      .tag {
        margin-right: 4px;
        line-height: 22px;
        &.effect {
          color: #3a84ff;
          background: #edf4ff;
        }
        &.operator {
          color: #fe9c00;
          background: #fff1db;
        }
        &.tolerationSeconds {
          color: #788779;
          background: #dde9de;
        }
      }
    }
  }
}
</style>
