<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    width="960"
    @shown="handleShown"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ $t('沙箱开发') }}</span>
        <bk-button
          :theme="'primary'"
          text
        >
          {{ $t('沙箱开发指引') }}
          <i class="paasng-icon paasng-jump-link"></i>
        </bk-button>
      </div>
    </div>
    <div
      class="sideslider-content"
      slot="content"
    >
      <bk-alert
        type="info"
        :title="
          $t(
            '沙箱提供云端开发环境，可在线修改运行代码。每个模块仅允许新建一个沙箱环境。如果沙箱环境在 2 个小时内没有任何操作，将自动被销毁。'
          )
        "
        closable
      ></bk-alert>
      <bk-button
        :theme="'primary'"
        class="mt15"
        @click="createSandbox"
      >
        {{ $t('新建沙箱') }}
      </bk-button>
      <bk-table
        style="margin-top: 15px"
        :data="sandboxEnvList"
        :outer-border="false"
        size="small"
        v-bkloading="{ isLoading: isTableLoading, zIndex: 10 }"
      >
        <bk-table-column
          :label="$t('模块')"
          prop="module_name"
        ></bk-table-column>
        <bk-table-column :label="$t('代码分支')">
          <template slot-scope="{ row }">
            {{ row.version_info_dict?.version_name }}
          </template>
        </bk-table-column>
        <bk-table-column
          :label="$t('创建时间')"
          prop="created"
        ></bk-table-column>
        <bk-table-column :label="$t('操作')">
          <template slot-scope="{ row }">
            <bk-button
              :theme="'primary'"
              text
              @click="toSandboxPage(row)"
            >
              {{ $t('进入') }}
            </bk-button>
            <bk-popconfirm
              trigger="click"
              ext-cls="sandbox-destroy-cls"
              width="288"
              @confirm="handleDestroy(row)"
            >
              <div slot="content">
                <div class="custom">
                  <i class="bk-icon icon-info-circle-shape pr5 content-icon"></i>
                  <div class="content-text">{{ $t('确认销毁沙箱开发环境吗？') }}</div>
                </div>
              </div>
              <bk-button
                :theme="'primary'"
                text
                class="ml10"
              >
                {{ $t('销毁') }}
              </bk-button>
            </bk-popconfirm>
          </template>
        </bk-table-column>
      </bk-table>
    </div>
  </bk-sideslider>
</template>

<script>
export default {
  name: 'SandboxSideslider',
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    env: {
      type: String,
    },
  },
  data() {
    return {
      sandboxEnvList: [],
      isTableLoading: false,
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
    appCode() {
      return this.$route.params.id;
    },
  },
  methods: {
    createSandbox() {
      this.$emit('create-sandbox');
    },
    handleShown() {
      this.getSandboxList();
    },
    toSandboxPage(row) {
      this.$router.push({
        name: 'sandbox',
        query: {
          code: this.appCode,
          module: row.module_name,
          env: this.env,
        },
      });
    },
    // 获取沙箱列表
    async getSandboxList() {
      this.isTableLoading = true;
      try {
        const res = await this.$store.dispatch('sandbox/getSandboxList', {
          appCode: this.appCode,
        });
        this.sandboxEnvList = res;
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isTableLoading = false;
      }
    },
    // 销毁沙箱
    async handleDestroy(row) {
      try {
        await this.$store.dispatch('sandbox/destroySandbox', {
          appCode: this.appCode,
          moduleId: row.module_name,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('销毁成功！'),
        });
        this.getSandboxList();
      } catch (e) {
        this.catchErrorHandler(e);
      }
    },
  },
};
</script>

<style lang="scss" scoped>
.header-box {
  display: flex;
  justify-content: space-between;
}
.sideslider-content {
  padding: 24px;
}
.sandbox-destroy-cls {
  .custom {
    font-size: 14px;
    line-height: 24px;
    color: #63656e;
    padding-bottom: 16px;
    .content-icon {
      color: #ea3636;
      position: absolute;
      top: 22px;
    }
    .content-text {
      display: inline-block;
      margin-left: 20px;
    }
  }
}
</style>
