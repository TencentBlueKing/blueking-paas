<template>
  <div
    class="env-var-display-container"
    v-bkloading="{ isLoading: isLoading, zIndex: 10 }"
  >
    <bk-alert
      type="info"
      class="mb-16"
    >
      <span slot="title">
        {{ $t('此处展示的内置变量不包含增强服务所写入的环境变量，更多说明请参考') }}
        <a
          class="ml5"
          :href="GLOBAL.DOC.ENV_VAR_INLINE"
          target="_blank"
        >
          {{ $t('内置环境变量说明') }}
          <i class="paasng-icon paasng-jump-link"></i>
        </a>
      </span>
    </bk-alert>
    <div class="top-box flex-row align-items-center">
      <bk-radio-group
        v-model="envSelected"
        class="env-select-group-cls"
      >
        <bk-radio-button value="stag">{{ $t('预发布环境') }}</bk-radio-button>
        <bk-radio-button value="prod">{{ $t('生产环境') }}</bk-radio-button>
      </bk-radio-group>
      <bk-input
        v-model="searchKey"
        class="flex-shrink-0"
        style="width: 320px"
        :placeholder="$t('搜索变量名/变量值/描述')"
        :clearable="true"
        :right-icon="'bk-icon icon-search'"
      ></bk-input>
    </div>
    <div class="info-header mt-16 flex-row align-items-center flex-shrink-0">
      <div class="var">{{ $t('变量名') }}</div>
      <div class="value">{{ $t('变量值') }}</div>
    </div>
    <ul class="env-var-list">
      <template v-if="filteredEnvVars.length > 0">
        <li
          v-for="(item, index) in filteredEnvVars"
          :key="`env-var-${index}`"
          class="flex-row align-items-center"
        >
          <div class="key text-ellipsis">
            <div class="env-content text-ellipsis">
              <span
                style="padding-bottom: 2px"
                v-bk-tooltips="{ content: getTooltipContent(item), disabled: !item.description }"
                v-dashed="{ disabled: !item.description }"
              >
                {{ item.key }}
              </span>
            </div>
            <i
              v-copy="item.key"
              class="paasng-icon paasng-general-copy copy-icon"
            />
          </div>
          <div :class="['value text-ellipsis', { sensitive: !item.is_sensitive }]">
            <div
              class="env-content text-ellipsis"
              v-bk-overflow-tips
            >
              <div
                v-if="item.is_sensitive"
                class="sensitive-wrapper"
              >
                <span
                  v-for="dot in 6"
                  class="sensitive-dot"
                  :key="dot"
                ></span>
              </div>
              <template v-else>
                {{ item.value || '--' }}
              </template>
            </div>
            <i
              v-if="!item.is_sensitive"
              v-copy="item.value"
              class="paasng-icon paasng-general-copy copy-icon"
            />
          </div>
        </li>
      </template>
      <template v-else>
        <bk-exception
          class="exception-wrap-item exception-part mt-24"
          :type="searchKey ? 'search-empty' : 'empty'"
          scene="part"
        ></bk-exception>
      </template>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'EnvVarContent',
  props: {
    appCode: {
      type: String,
      required: true,
    },
    moduleId: {
      type: String,
      required: true,
    },
  },
  data() {
    return {
      isLoading: false,
      envSelected: 'stag',
      allBuiltInEnvVars: {
        stag: [],
        prod: [],
      },
      searchKey: '',
    };
  },
  created() {
    this.getAllBuiltInEnvVars();
  },
  computed: {
    // 根据搜索关键字过滤环境变量
    filteredEnvVars() {
      const envVars = this.allBuiltInEnvVars[this.envSelected] || [];
      if (!this.searchKey?.trim()) {
        return envVars;
      }
      const keyword = this.searchKey.toLowerCase().trim();
      return envVars.filter(
        (item) =>
          item.key?.toLowerCase().includes(keyword) ||
          item.description?.toLowerCase().includes(keyword) ||
          (!item.is_sensitive && item.value?.toString().toLowerCase().includes(keyword))
      );
    },
  },
  methods: {
    getTooltipContent(item) {
      if (item.is_sensitive) {
        return `${item.description}，${this.$t('已脱敏处理')}`;
      }
      return item.description;
    },
    // 获取全量内置环境变量
    async getAllBuiltInEnvVars() {
      this.isLoading = true;
      try {
        const res = await this.$store.dispatch('envVar/getAllBuiltInEnvVars', {
          appCode: this.appCode,
          moduleId: this.moduleId,
        });
        this.allBuiltInEnvVars = {
          stag: res.stag || [],
          prod: res.prod || [],
        };
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.env-var-display-container {
  display: flex;
  flex-direction: column;
  height: 100%;
  .env-select-group-cls {
    /deep/ .bk-form-radio-button .bk-radio-button-input:checked + .bk-radio-button-text {
      color: #fff;
      background-color: #3a84ff;
      border-color: #3a84ff;
    }
  }
  .env-var-list {
    overflow-y: auto;
    &::-webkit-scrollbar {
      width: 6px;
      height: 6px;
      background-color: #fafafa;
    }
    &::-webkit-scrollbar-thumb {
      height: 6px;
      border-radius: 4px;
      background-color: #ccc;
    }
    li {
      color: #4d4f56;
      font-size: 12px;
      border-bottom: 1px solid #dcdee5;
      &:hover {
        background: #f5f7fa;
        i {
          display: block !important;
        }
      }
      .key,
      .value {
        display: flex;
        align-items: center;
        height: 40px;
        width: 50%;
        padding: 0 16px;
        .env-content {
          flex: 1;
          span {
            display: inline-block;
          }
        }
        i {
          display: none;
          flex-shrink: 0;
          color: #3a84ff;
          cursor: pointer;
        }
      }
      .sensitive-wrapper {
        display: flex;
        align-items: center;
        gap: 4px;
        .sensitive-dot {
          width: 6px;
          height: 6px;
          display: inline-block;
          border-radius: 50%;
          background-color: #4d4f56;
        }
      }
    }
  }
  .info-header {
    height: 42px;
    font-size: 12px;
    color: #313238;
    background: #fafbfd;
    padding-right: 6px;
    .var,
    .value {
      width: 50%;
      padding: 0 16px;
    }
  }
  i.paasng-jump-link {
    font-size: 14px;
    transform: translateY(0px);
  }
}
</style>
