<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    width="960"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ $t('组件详情') }}</span>
        <span class="sub-title">{{ name }}</span>
      </div>
    </div>
    <div
      class="sideslider-content"
      slot="content"
    >
      <div class="view-title">{{ $t('基本信息') }}</div>
      <DetailsRow
        v-for="(val, key) in baseInfoMap"
        :label-width="100"
        :key="key"
      >
        <template slot="label">
          {{ `${val}：` }}
        </template>
        <template slot="value">
          <span v-if="key === 'chat'">{{ name + version }}</span>
          <span v-else>{{ displayData[key] || '--' }}</span>
        </template>
      </DetailsRow>
      <div class="view-title">{{ $t('部署信息') }}</div>
      <DetailsRow
        v-for="(val, key) in deployedMap"
        :label-width="100"
        :key="key"
      >
        <template slot="label">
          {{ `${val}：` }}
        </template>
        <template slot="value">
          <span v-if="key === 'chat'">{{ name + version }}</span>
          <span v-else>{{ displayData[key] || '--' }}</span>
        </template>
      </DetailsRow>
      <div class="view-title">{{ $t('工作负载状态') }}</div>
      <bk-table
        :data="detailData.workloads"
        :shift-multi-checked="true"
        dark-header
      >
        <bk-table-column
          label="Kind"
          prop="kind"
          :width="100"
          show-overflow-tooltip
        ></bk-table-column>
        <bk-table-column
          label="Name"
          prop="name"
          :width="100"
          show-overflow-tooltip
        ></bk-table-column>
        <bk-table-column
          label="Summary"
          prop="summary"
          :width="130"
        >
          <div
            slot-scope="{ row }"
            class="summary-wrapper"
          >
            <template v-if="!row.summary">--</template>
            <div
              v-else
              v-for="item in row.summary?.split(',')"
              :key="item"
              class="item"
            >
              {{ item }}
            </div>
          </div>
        </bk-table-column>
        <bk-table-column
          label="Conditions"
          prop="conditions"
        >
          <div slot-scope="{ row }">
            <!-- JSON格式预览 -->
            <vue-json-pretty
              :data="row.conditions"
              :deep="1"
              :show-length="true"
              :highlight-mouseover-node="true"
            />
          </div>
        </bk-table-column>
      </bk-table>
    </div>
  </bk-sideslider>
</template>

<script>
import DetailsRow from '@/components/details-row';
import VueJsonPretty from 'vue-json-pretty';
import 'vue-json-pretty/lib/styles.css';
export default {
  name: 'DetailComponentsSideslider',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    name: {
      type: String,
      default: '',
    },
    detailData: {
      type: Object,
      default: () => {},
    },
  },
  components: {
    DetailsRow,
    VueJsonPretty,
  },
  data() {
    return {
      baseInfoMap: {
        releaseName: this.$t('Release 名称'),
        namespace: this.$t('命名空间'),
        releaseVersion: this.$t('版本号'),
        chartName: 'Chart',
        chartVersion: `Chart ${this.$t('版本')}`,
        app_version: `APP ${this.$t('版本')}`,
      },
      deployedMap: {
        status: this.$t('状态'),
        deployed_at: this.$t('部署时间'),
        description: this.$t('部署说明'),
      },
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
    displayData() {
      const { chart = {}, release = {} } = this.detailData;
      return {
        ...chart,
        ...release,
        chartName: chart.name,
        chartVersion: chart.version,
        releaseName: release.name,
        releaseVersion: release.version,
      };
    },
  },
};
</script>

<style lang="scss" scoped>
.header-box {
  display: flex;
  align-items: center;
  .sub-title {
    height: 18px;
    line-height: 18px;
    font-size: 14px;
    margin-left: 10px;
    padding-left: 8px;
    color: #979ba5;
    border-left: 1px solid #dcdee5;
  }
}
.sideslider-content {
  padding: 24px;
  .summary-wrapper {
    padding: 10px 0;
    display: flex;
    flex-direction: column;
    .item {
      line-height: 1.3;
      margin-bottom: 8px;
      &:last-child {
        margin-bottom: 0;
      }
    }
  }
  .view-title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
    margin: 24px 0 12px 0;
    &:first-child {
      margin-top: 0;
    }
  }
}
</style>
