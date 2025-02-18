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
        :data="tableData"
        :shift-multi-checked="true"
        dark-header
      >
        <bk-table-column
          label="Kind"
          prop="kind"
        ></bk-table-column>
        <bk-table-column
          label="Name"
          prop="name"
        ></bk-table-column>
        <bk-table-column
          label="Ready"
          prop="Ready"
        ></bk-table-column>
        <bk-table-column
          label="Up-to-date"
          prop="Up-to-date"
        ></bk-table-column>
        <bk-table-column
          label="Available"
          prop="Available"
        ></bk-table-column>
        <bk-table-column
          label="Conditions"
          prop="conditions"
        >
          <div slot-scope="{ row }">{{ row.conditions }}</div>
        </bk-table-column>
      </bk-table>
    </div>
  </bk-sideslider>
</template>

<script>
import DetailsRow from '@/components/details-row';
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
  },
  data() {
    return {
      baseInfoMap: {
        name: this.$t('Release 名称'),
        namespace: this.$t('命名空间'),
        version: this.$t('版本号'),
        // chartText = name + version
        chartText: 'Chart',
        app_version: this.$t('APP 版本'),
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
      const { chart, release } = this.detailData;
      return {
        ...chart,
        ...release,
        chartText: chart.name + chart.version,
      };
    },
    tableData() {
      return this.detailData.workloads.map((v) => {
        const ret = this.parseStringToObject(v.summary);
        return {
          ...v,
          ...ret,
        };
      });
    },
  },
  methods: {
    parseStringToObject(str) {
      const result = {};
      const parts = str.split(', ');

      parts.forEach((part) => {
        const [key, value] = part.split(': ').map((item) => item.trim());
        result[key] = value;
      });
      return result;
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
