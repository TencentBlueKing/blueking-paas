<template>
  <div class="image-container">
    <paas-content-loader
      class="image-content"
      :is-loading="isLoading"
      :is-transition="false"
      :offset-top="0"
      :offset-left="0"
      placeholder="roles-loading"
    >
      <div class="middle ps-main mirror-credentials">
        <div class="flex-row align-items-center">
          <span class="base-info-title">
            {{ $t('镜像凭证') }}
          </span>
          <div
            class="add-container"
            @click="handleCreate"
          >
            <i class="paasng-icon paasng-plus-circle-shape pl10" />
            {{ $t('新建镜像凭证') }}
          </div>
        </div>
        <div class="credential-tips">{{ $t('私有镜像需要提供镜像凭证来拉取镜像，镜像凭证添加后应用下所有模块都可以使用。') }}</div>
        <bk-table
          v-if="credentialList.length"
          v-bkloading="{ isLoading: tableLoading, opacity: 1 }"
          :data="credentialList"
          size="small"
          ext-cls="mirror-table-cls"
          :outer-border="false"
          :pagination="pagination"
          @page-change="pageChange"
          @page-limit-change="limitChange"
        >
          <div slot="empty">
            <table-empty empty />
          </div>
          <bk-table-column :label="$t('名称')">
            <template slot-scope="props">
              {{ props.row.name || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('账号')">
            <template slot-scope="props">
              {{ props.row.username || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column :label="$t('描述')">
            <template slot-scope="props">
              {{ props.row.description || '--' }}
            </template>
          </bk-table-column>
          <bk-table-column
            width="150"
            :label="$t('操作')"
          >
            <template slot-scope="props">
              <bk-button
                class="mr10"
                text
                theme="primary"
                @click="handleEdit(props.row)"
              >
                {{ $t('编辑') }}
              </bk-button>
              <bk-button
                class="mr10"
                text
                theme="primary"
                @click="handleDelete(props.row)"
              >
                {{ $t('删除') }}
              </bk-button>
            </template>
          </bk-table-column>
        </bk-table>
      </div>
    </paas-content-loader>
    <create-credential
      ref="credentialDialog"
      :config="visiableDialogConfig"
      :type="type"
      :credential-detail="credentialDetail"
      @updata="updateCredential"
      @confirm="addCredential"
      @close="isCreateCredential"
    />
  </div>
</template>

<script>
import i18n from '@/language/i18n.js';
import _ from 'lodash';
import CreateCredential from './create.vue';
export default {
  components: {
    CreateCredential,
  },
  props: {
    list: {
      type: Array,
      default: () => [],
    },
  },
  data() {
    return {
      credentialList: [],
      pagination: {
        current: 1,
        count: 0,
        limit: 10,
      },
      visiableDialogConfig: {
        visiable: false,
        loading: false,
        title: i18n.t('新增凭证'),
      },
      isLoading: false,
      visiableDialog: false,
      tableLoading: false,
      type: 'new',
      credentialDetail: {},
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    curAppCode() {
      return this.$store.state.curAppCode;
    },
  },
  watch: {
    curAppCode() {
      this.getCredentialList();
      // this.isLoading = true;
    },
    list(value) {
      // 镜像凭证初始化
      this.credentialList = value;
    },
  },
  methods: {

    // 获取凭证列表
    async getCredentialList() {
      this.tableLoading = true;
      try {
        const { appCode } = this;
        const res = await this.$store.dispatch('credential/getImageCredentialList', { appCode });
        this.credentialList = res;
        this.credentialList.forEach((item) => {
          item.password = '';
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.tableLoading = false;
        setTimeout(() => {
          this.isLoading = false;
        }, 500);
      }
    },

    async addCredential(formData) {
      this.visiableDialogConfig.loading = true;
      const { appCode } = this;
      const data = formData;
      try {
        await this.$store.dispatch('credential/addImageCredential', { appCode, data });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('添加成功'),
        });
        this.$refs.credentialDialog.handleCancel();
        this.getCredentialList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      } finally {
        this.visiableDialogConfig.loading = false;
      }
    },

    async updateCredential(formData) {
      const { appCode } = this;
      const crdlName = formData.name;
      const data = formData;
      try {
        await this.$store.dispatch('credential/updateImageCredential', { appCode, crdlName, data });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('更新成功'),
        });
        this.$refs.credentialDialog.handleCancel();
        this.getCredentialList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      }
    },

    async deleteImageCredential(name) {
      const { appCode } = this;
      const crdlName = name;
      try {
        await this.$store.dispatch('credential/deleteImageCredential', { appCode, crdlName });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功'),
        });
        this.visiableDialogConfig.visiable = false;
        this.getCredentialList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || this.$t('接口异常'),
        });
      }
    },

    // 新增凭证
    handleCreate() {
      this.visiableDialogConfig.visiable = true;
      this.visiableDialogConfig.title = this.$t('新增凭证');
      this.type = 'new';
      this.credentialDetail = {};
    },

    // 编辑凭证
    handleEdit(data) {
      this.visiableDialogConfig.visiable = true;
      this.visiableDialogConfig.title = this.$t('编辑凭证');
      this.type = 'edit';
      this.credentialDetail = _.cloneDeep(data);
    },

    pageChange(page) {
      if (this.currentBackup === page) {
        return;
      }
      this.pagination.current = page;
    },

    limitChange(currentLimit) {
      this.pagination.limit = currentLimit;
      this.pagination.current = 1;
    },

    handleDelete(data) {
      this.$bkInfo({
        extCls: 'delete-image-credential',
        title: this.$t('确认删除镜像凭证：') + data.name,
        subTitle: this.$t('删除凭证后，使用该凭证的镜像将无法部署'),
        confirmFn: () => {
          this.deleteImageCredential(data.name);
        },
      });
      this.$nextTick(() => {
        this.addTitle(data.name);
      });
    },

    isCreateCredential() {
      this.visiableDialogConfig.visiable = false;
      this.visiableDialog = false;
    },

    addTitle(name) {
      document.querySelector('.delete-image-credential .bk-dialog-header-inner').setAttribute('title', name);
    },
  },
};
</script>

<style lang="scss" scoped>
.image-container {
  .ps-top-bar {
    padding: 0 20px;
  }
  .image-content {
    background: #fff;
    padding-top: 0;
  }
}
.header-title {
  display: flex;
  align-items: center;
  .app-code {
    color: #979ba5;
  }
  .arrows {
    margin: 0 9px;
    transform: rotate(-90deg);
    font-size: 12px;
    font-weight: 600;
    color: #979ba5;
  }
}

.mirror-credentials {
  padding: 20px 0;
  border-bottom: 1px solid #dcdee5;
  .base-info-title {
    color: #313238;
    font-size: 14px;
    font-weight: bold;
    width: 70px;
    text-align: right;
  }
  .add-container{
    color: #3A84FF;
    font-size: 12px;
    cursor: pointer;
    padding-left: 10px;
    i{
      padding-right: 3px;
    }
  }

  .credential-tips {
    padding: 0 15px;
    margin-top: 8px;
    color: #979BA5;
    font-size: 12px;
  }
}
.mirror-table-cls {
  margin-top: 20px;
  padding: 0 15px;
  /deep/ .bk-table-row-last td {
    border-bottom: none !important;
  }
}
</style>
