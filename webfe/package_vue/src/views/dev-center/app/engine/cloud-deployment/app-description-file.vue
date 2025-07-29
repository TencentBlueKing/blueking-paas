<template>
  <div
    v-if="showVarPresetList.length"
    :class="['app-description-file', { expanded: isExpanded }]"
  >
    <div
      class="table-header-cls"
      @click="toggleExpand"
    >
      <i class="paasng-icon paasng-right-shape mr5"></i>
      {{ $t('来自应用描述文件') }}
      <i
        class="paasng-icon paasng-info-line"
        v-bk-tooltips="{
          content: $t('应用描述文件中定义的环境变量无法在页面上修改，但可以在页面上添加同名变量以覆盖其值'),
          width: 280,
        }"
      ></i>
    </div>
    <bk-table
      v-if="isExpanded"
      :data="showVarPresetList"
      size="small"
      :outer-border="false"
      :show-header="false"
      :row-class-name="rowClassName"
      :key="updateIndex"
    >
      <bk-table-column prop="key">
        <template slot-scope="{ row }">
          <div class="flex-row align-items-center">
            <span
              class="env-key"
              v-bk-overflow-tips
            >
              {{ row.key || '--' }}
            </span>
            <i
              v-if="row.isPresent"
              class="paasng-icon paasng-remind"
              v-bk-tooltips="$t('环境变量已失效，因为页面上新增了同名的环境变量')"
            ></i>
          </div>
        </template>
      </bk-table-column>
      <bk-table-column :width="100">
        <template slot-scope="{ row }">
          {{ $t('否') }}
        </template>
      </bk-table-column>
      <bk-table-column prop="value">
        <template slot-scope="{ row }">
          <div v-bk-overflow-tips>
            {{ row.value || '--' }}
          </div>
        </template>
      </bk-table-column>
      <bk-table-column prop="environment_name">
        <template slot-scope="{ row }">
          <div v-bk-overflow-tips>
            {{ envMap[row.environment_name] }}
          </div>
        </template>
      </bk-table-column>
      <bk-table-column prop="description">
        <template slot-scope="{ row }">
          <div v-bk-overflow-tips>
            {{ row.description || '--' }}
          </div>
        </template>
      </bk-table-column>
      <bk-table-column width="140"></bk-table-column>
    </bk-table>
  </div>
</template>

<script>
import appBaseMixin from '@/mixins/app-base-mixin';
export default {
  name: 'AppDescriptionFile',
  mixins: [appBaseMixin],
  props: {
    envVars: {
      type: Array,
      default: () => [],
    },
    activeEnv: {
      type: String,
      default: 'all',
    },
    orderBy: {
      type: String,
      default: '',
    },
  },
  data() {
    return {
      data: [],
      isExpanded: true,
      envMap: {
        _global_: this.$t('所有环境'),
        stag: this.$t('预发布环境'),
        prod: this.$t('生产环境'),
      },
      showVarPresetList: [],
      updateIndex: 0,
    };
  },
  watch: {
    envVars() {
      this.data = this.formatVarPreset(this.envVars, this.data);
    },
    activeEnv() {
      this.showVarPresetList = this.getShowVarPresetList();
    },
    orderBy() {
      this.getConfigVarPreset();
    },
    data: {
      handler() {
        this.showVarPresetList = this.getShowVarPresetList();
      },
      deep: true,
    },
  },
  created() {
    this.getConfigVarPreset();
  },
  methods: {
    // 获取当前环境下的预设变量
    getShowVarPresetList() {
      if (this.activeEnv === 'all') {
        return this.data;
      }
      return this.data.filter((item) => item.environment_name === this.activeEnv);
    },
    toggleExpand() {
      this.isExpanded = !this.isExpanded;
    },
    // 获取预设环境变量
    async getConfigVarPreset() {
      try {
        const result = await this.$store.dispatch('envVar/getConfigVarPreset', {
          appCode: this.appCode,
          moduleId: this.curModuleId,
          params: {
            order_by: this.orderBy,
          },
        });
        this.data = this.formatVarPreset(this.envVars, result);
        this.$emit('var-preset-length', this.data.length);
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
    formatVarPreset(envVarList, presetList) {
      this.updateIndex += 1;
      const envVarMap = new Map(envVarList.map((item) => [item.key, item]));

      presetList.forEach((item) => {
        const duplicateItem = envVarMap.get(item.key);
        if (duplicateItem) {
          // 检查冲突条件
          item.isPresent = this.hasConflict(item, duplicateItem);
        } else {
          // 没有重复项，删除 isPresent 属性
          delete item.isPresent;
        }
      });
      return presetList;
    },
    // 是否存在冲突
    hasConflict(item, duplicateItem) {
      const isGlobalConflict = item.environment_name === '_global_' || duplicateItem.environment_name === '_global_';
      const isSameEnvironmentConflict = duplicateItem.environment_name === item.environment_name;
      return isGlobalConflict || isSameEnvironmentConflict;
    },
    rowClassName({ row }) {
      return row.isPresent ? 'already-exists' : '';
    },
  },
};
</script>

<style lang="scss" scoped>
.app-description-file {
  &.expanded .table-header-cls {
    .paasng-right-shape {
      transform: rotate(90deg);
    }
  }
  /deep/ .bk-table-row.already-exists .cell {
    color: #c4c6cc;
  }
  .env-key {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .paasng-remind {
    margin-left: 5px;
    font-size: 14px;
    color: #ea3636;
    transform: translateY(0);
  }
  .table-header-cls {
    cursor: pointer;
    display: flex;
    align-items: center;
    height: 42px;
    padding: 0 15px;
    background: #fafbfd;
    font-size: 12px;
    color: #4d4f56;
    border-bottom: 1px solid #dfe0e5;
    i {
      transform: translateY(0);
      font-size: 14px;
    }
    .paasng-right-shape {
      margin-left: -2px;
      transition: 0.2s all;
      cursor: pointer;
      color: #4d4f56;
      transform: rotate(0deg);
    }
    .paasng-info-line {
      margin-left: 5px;
      color: #979ba5;
    }
  }
}
</style>
