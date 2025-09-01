<template>
  <div class="codecc-base-info-container card-style" v-bkloading="{ isLoading: basicLoading, zIndex: 10 }">
    <bk-alert
      type="info"
      :show-icon="false"
    >
      <div
        slot="title"
        class="codecc-base-alert-cls"
      >
        <i class="bk-icon icon-info"></i>
        {{ $t('CodeCC 工具信息展示的是最新的测试版本，如需修改') }}&nbsp;
        {{ $t('可前往') }}&nbsp;
        <bk-button
          :text="true"
          title="primary"
          size="small"
          @click="handleToConfig('tool.json')">
          tool.json
        </bk-button>&nbsp;{{ $t('和') }}&nbsp;
        <bk-button
          :text="true"
          title="primary"
          size="small"
          @click="handleToConfig('checkers.json')">
          checkers.json
        </bk-button>
        &nbsp;{{ $t('修改后重新测试') }}
      </div>
    </bk-alert>
    <ul class="info">
      <li
        class="item"
        v-for="(key, value) in BASICINFOMAP"
        :key="key"
      >
        <div class="label">{{ key }}</div>
        <div :class="['value', { num: value === 'checkerNum' }]">
          <a
            v-if="value === 'checkerNum'"
            href="javascript:void(0);"
            @click="handleToConfig('checkers.json')"
          >{{ basicInfo[value] || '--' }}</a>
          <span v-else>{{ basicInfo[value] || '--' }}</span>
          <span class="tag ml15" v-if="tags[value]">{{ tags[value] }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<script>
export default {
  name: 'CodeccBaseInfo',
  data() {
    return {
      basicLoading: true,
      basicInfo: {},
      BASICINFOMAP: {
        type: this.$t('插件类型'),
        name: this.$t('插件标识'),
        displayName: this.$t('插件名称'),
        devLanguage: this.$t('开发语言'),
        toolCnTypes: this.$t('工具类别'),
        langList: this.$t('适用语言'),
        needBuildScript: this.$t('业务编译脚本'),
        checkerNum: this.$t('规则数'),
        description: this.$t('工具描述'),
      },
      tags: {
        type: this.$t('不可修改'),
        displayName: this.$t('不可修改'),
        langList: this.$t('不可删除语言，可新增语言'),
        needBuildScript: this.$t('不可将「不需要」编译修改为「需要」编译'),
      },
    };
  },
  computed: {
    pdId() {
      return this.$route.params.pluginTypeId;
    },
    pluginId() {
      return this.$route.params.id;
    },
    curPluginInfo() {
      return this.$store.state.plugin.curPluginInfo;
    },
  },
  created() {
    this.getCodeccBasicInfo();
  },
  methods: {
    handleToConfig(suffix) {
      const { repository } = this.curPluginInfo;
      const url = repository.replace(/\.git$/, `/blob/master/${suffix}`);
      window.open(url, '_blank');
    },
    async getCodeccBasicInfo() {
      this.basicLoading = true;
      try {
        const res = await this.$store.dispatch('plugin/getCodeccBasicInfo', {
          pdId: this.pdId,
          pluginId: this.pluginId,
        });
        this.basicInfo = {
          ...res,
          type: 'CodeCC 工具',
          toolCnTypes: res.toolCnTypes.join('、'),
          langList: res.langList.length ? res.langList.join('、') : '--',
          needBuildScript: res.needBuildScript ? this.$t('需要业务提供') : this.$t('不需要业务提供'),
        };
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.basicLoading = false;
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.codecc-base-info-container {
  @mixin flex-center {
    display: flex;
    align-items: center;
  }
  padding: 16px 24px;
  .info {
    margin-top: 16px;
    .item {
      @include flex-center;
      height: 42px;
      border: 1px solid #dcdee5;
      border-top: none;
      font-size: 12px;
      color: #313238;
      &:first-child {
        border-top: 1px solid #dcdee5;
      }
      .label,
      .value {
        height: 100%;
        padding: 0 16px;
        &.num {
          color: #3a84ff;
        }
        .tag {
          display: inline-block;
          font-size: 10px;
          color: #63656E;
          line-height: 16px;
          height: 16px;
          padding: 0 5px;
          background: #F0F1F5;
          border-radius: 2px;
          white-space: nowrap;
        }
      }
      .label {
        @include flex-center;
        width: 152px;
        flex-shrink: 1;
        background: #fafbfd;
        border-right: 1px solid #dcdee5;
      }
      .value {
        @include flex-center;
        flex: 1;
        color: #63656e;
      }
    }
  }
  .codecc-base-alert-cls {
    display: flex;
    align-items: center;
    font-size: 12px;
    /deep/ .bk-button-text.bk-button-small {
      padding: 0;
    }
  }
}
</style>
