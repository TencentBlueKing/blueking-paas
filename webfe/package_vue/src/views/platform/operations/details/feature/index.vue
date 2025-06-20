<template>
  <div class="app-feature-container">
    <div class="top-box">
      <bk-input
        v-model="searchValue"
        :placeholder="$t('请输入特性名称')"
        :right-icon="'bk-icon icon-search'"
        style="width: 400px"
        clearable
      ></bk-input>
    </div>
    <bk-table
      :data="filteredData"
      ref="tableRef"
      size="small"
      v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
    >
      <bk-table-column
        v-for="column in columns"
        v-bind="column"
        :label="column.label"
        :prop="column.prop"
        :key="column.prop"
        show-overflow-tooltip
        :width="column.width"
      >
        <template slot-scope="{ row }">
          <span v-if="column.prop === 'default_feature_flag'">{{ row[column.prop] ? $t('开启') : $t('关闭') }}</span>
          <bk-switcher
            v-else-if="column.prop === 'effect'"
            v-model="row[column.prop]"
            theme="primary"
            @change="switcherChange(row, $event)"
          ></bk-switcher>
          <div v-else-if="column.prop === 'custom-actions'">
            <!-- 当前状态与默认值一致，禁用 -->
            <bk-button
              text
              :disabled="row.effect === row.default_feature_flag"
              @click="handleRestDefault(row)"
            >
              {{ $t('恢复默认值') }}
            </bk-button>
          </div>
          <span v-else>{{ row[column.prop] || '--' }}</span>
        </template>
      </bk-table-column>
    </bk-table>
  </div>
</template>

<script>
import { debounce } from 'lodash';

export default {
  name: 'appFeature',
  data() {
    return {
      searchValue: '',
      featureList: [],
      filteredData: [],
      isTableLoading: false,
      columns: [
        {
          label: this.$t('特性名称'),
          prop: 'label',
        },
        {
          label: this.$t('默认值'),
          prop: 'default_feature_flag',
        },
        {
          label: this.$t('状态'),
          prop: 'effect',
        },
        {
          label: this.$t('操作'),
          prop: 'custom-actions',
          width: 150,
        },
      ],
    };
  },
  computed: {
    appCode() {
      return this.$route.params.code;
    },
  },
  watch: {
    searchValue: 'debounceFilterFeatures',
  },
  created() {
    this.getFeatureList();
  },
  methods: {
    // 获取特性列表
    async getFeatureList() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('tenantOperations/getFeatureList', {
          appCode: this.appCode,
        });
        // default_feature_flag 和 effect 不相等的排在前面
        this.featureList = res.sort((a, b) => {
          const diffA = a.default_feature_flag !== a.effect;
          const diffB = b.default_feature_flag !== b.effect;
          return diffB - diffA;
        });
        this.filteredData = [...this.featureList];
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        setTimeout(() => {
          this.isTableLoading = false;
        }, 200);
      }
    },
    // 更新特性
    async updateFeatureFlags(data) {
      try {
        await this.$store.dispatch('tenantOperations/updateFeatureFlags', {
          appCode: this.appCode,
          data,
        });
        const messageTxt = data.effect ? this.$t('特性已开启') : this.$t('特性已关闭');
        this.getFeatureList();
        this.$paasMessage({
          theme: 'success',
          message: messageTxt,
        });
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    // 切换状态
    switcherChange(row, val) {
      const params = {
        name: row.name,
        effect: val,
      };
      this.updateFeatureFlags(params);
    },
    // 恢复默认值
    handleRestDefault(row) {
      const params = {
        name: row.name,
        effect: row.default_feature_flag,
      };
      this.updateFeatureFlags(params);
    },
    // 关键字搜索
    debounceFilterFeatures: debounce(function () {
      if (this.searchValue) {
        this.filteredData = this.featureList.filter((f) => {
          return f.label?.includes(this.searchValue);
        });
      } else {
        this.filteredData = this.featureList;
      }
    }, 300),
  },
};
</script>

<style lang="scss" scoped>
.app-feature-container {
  .top-box {
    margin-bottom: 16px;
  }
}
</style>
