<template>
  <div class="right-main">
    <paas-content-loader
      class="app-container middle"
      :is-loading="isLoading"
      placeholder="persistent-storage-loading"
    >
      <section class="storage-container">
        <!-- 无数据 -->
        <section
          v-if="!persistentStorageList.length"
          style="margin-top: 38px"
        >
          <bk-exception
            class="exception-wrap-item exception-part"
            type="empty"
            scene="part"
          >
            <p class="mt10 exception-text">{{ $t('暂无持久存储资源') }}</p>
            <p class="exception-text">
              {{ $t('持久化存储使用腾讯云 CFS，可用于多个模块、进程间共享数据。') }}
              <bk-button
                theme="primary"
                text
                style="font-size: 12px"
              >
                {{ $t('查看计费方式') }}
              </bk-button>
            </p>
            <p class="guide-link mt15">
              <bk-button
                theme="primary"
                text
                style="font-size: 12px"
                @click="handlerPersistentStorage"
              >
                {{ $t('申请持久存储') }}
              </bk-button>
            </p>
          </bk-exception>
        </section>
        <template v-else>
          <div class="top">
            <bk-button
              theme="primary"
              class="mr10"
              @click="handlerPersistentStorage"
            >
              <i class="paasng-icon paasng-plus mr5 plus" />
              {{ $t('新增持久存储') }}
            </bk-button>
            <span class="tips">
              <i class="paasng-icon paasng-info-line tips-line" />
              <span>
                {{ $t('持久化存储使用腾讯云 CFS，可用于多个模块、进程间共享数据。持久存储申请后就会产生实际的费用，请按需申请，不用的资源请及时删除。') }}
              </span>
              <bk-button
                theme="primary"
                text
                style="font-size: 12px"
                @click="viewBillingMethod"
              >
                {{ $t('查看计费方式') }}
              </bk-button>
            </span>
          </div>
          <!-- 存储列表 -->
          <section
            class="collapse-panel"
            v-for="item in persistentStorageList"
            :key="item.name"
          >
            <section
              :class="['panel-item', { active: item.isExpanded }]"
              @click="handlerPanelChage(item)"
              @mouseenter="curHoverPanels = item.name"
              @mouseleave="curHoverPanels = ''"
            >
              <div class="icon-warpper">
                <i class="paasng-icon paasng-play-shape"></i>
              </div>
              <div class="main">
                <p class="name">{{ item.name }}</p>
                <div class="info">
                  <span>{{ $t('生效环境') }}：{{ item.environment_name }}</span>
                  <span>{{ $t('容量') }}：{{ item.storage }}</span>
                  <span>{{ $t('已绑定模块数') }}：{{ item.binded_modules.length || 0 }}</span>
                </div>
              </div>
              <div
                class="delete"
                v-show="curHoverPanels === item.name"
                @click.stop="handlerDelete(item)"
              >
                <i class="paasng-icon paasng-delete"></i>
                {{ $t('删除') }}
              </div>
            </section>
            <section class="content" v-if="item.isExpanded">
              <bk-table
                :data="item.formatBindedModules"
                :outer-border="false"
                ext-cls="store-module-table-cls"
              >
                <bk-table-column
                  :label="$t('绑定模块')"
                  prop="module"
                  :width="150"
                ></bk-table-column>
                <bk-table-column
                  :label="$t('挂载目录')"
                  prop="path"
                ></bk-table-column>
              </bk-table>
            </section>
          </section>
        </template>
      </section>

      <!-- 新增持久存储 -->
      <bk-dialog
        v-model="storageDialogConfig.visible"
        theme="primary"
        :width="640"
        :mask-close="false"
        :title="$t('新增持久存储')"
        :auto-close="false"
        header-position="left"
      >
        <div slot="footer">
          <bk-button
            theme="primary"
            :loading="storageDialogConfig.isLoading"
            @click="handlerConfirm"
          >
            {{ $t('确定') }}
          </bk-button>
          <bk-button
            theme="default"
            @click="handlerCancel"
          >
            {{ $t('取消') }}
          </bk-button>
        </div>
        <section class="storage-dialog-content">
          <bk-alert type="error" :show-icon="false">
            <div slot="title">
              <i class="paasng-icon paasng-remind remind-cls"></i>
              {{ $t('持久存储会申请对应容量的腾讯云 CFS，新建后就会产生实际的费用，请按需申请。') }}
              <bk-button
                theme="primary"
                text
                style="font-size: 12px"
                @click="viewBillingMethod"
              >
                {{ $t('查看计费方式') }}
              </bk-button>
            </div>
          </bk-alert>
          <bk-form
            :label-width="localLanguage === 'en' ? 160 : 85"
            :model="createPersistentStorageData"
            ext-cls="form-cls"
            style="margin-top: 16px"
          >
            <bk-form-item
              :label="$t('生效环境')"
              :required="true"
              :property="'stage'"
            >
              <bk-radio-group v-model="createPersistentStorageData.stage">
                <bk-radio :value="'stag'">{{ $t('预发布环境') }}</bk-radio>
                <bk-radio :value="'prod'">{{ $t('生产环境') }}</bk-radio>
              </bk-radio-group>
            </bk-form-item>
            <bk-form-item
              :label="$t('容量')"
              :required="true"
              :property="'capacity'"
            >
              <bk-radio-group v-model="createPersistentStorageData.capacity">
                <bk-radio :value="'1Gi'">1Gi</bk-radio>
                <bk-radio :value="'2Gi'" :disabled="preReleaseEnvironment">2Gi</bk-radio>
                <bk-radio :value="'4Gi'" :disabled="preReleaseEnvironment">4Gi</bk-radio>
              </bk-radio-group>
              <p class="capacity-tips">{{ $t('容量无法更改，请合理评估容量') }}</p>
            </bk-form-item>
          </bk-form>
        </section>
      </bk-dialog>

      <!-- 删除持久存储 -->
      <bk-dialog
        v-model="delteDialogConfig.visible"
        theme="primary"
        :width="640"
        :mask-close="false"
        :title="`${$t('删除持久存储')} ${curDeleteData.name}`"
        :auto-close="false"
        header-position="left"
      >
        <div slot="footer">
          <bk-button
            theme="primary"
            :loading="delteDialogConfig.isLoading"
            :disabled="delteDialogConfig.isDisabled"
            @click="deletePersistentStorage"
          >
            {{ $t('确定') }}
          </bk-button>
          <bk-button
            theme="default"
            @click="handlerDeleteCancel"
          >
            {{ $t('取消') }}
          </bk-button>
        </div>
        <section class="del-storage-dialog-content">
          <bk-alert type="error" :show-icon="false">
            <div slot="title">
              <i class="paasng-icon paasng-remind remind-cls"></i>
              {{ deleteAlertTip }}
            </div>
          </bk-alert>
          <div class="delete-tips spacing-x1">
            {{ $t('请完整输入') }} <code>{{ appCode }}</code> {{ $t('来确认删除存储！') }}
          </div>
          <bk-input v-model="deleteName"></bk-input>
        </section>
      </bk-dialog>
    </paas-content-loader>
  </div>
</template>

<script>const defaultSourceType = 'PersistentStorage';

export default {
  name: 'AppPersistentStorage',
  data() {
    return {
      isLoading: true,
      panels: [],
      persistentStorageList: [],
      storageDialogConfig: {
        visible: false,
        isLoading: false,
      },
      delteDialogConfig: {
        visible: false,
        isLoading: false,
        isDisabled: true,
      },
      createPersistentStorageData: {
        stage: 'stag',
        capacity: '1Gi',
      },
      curHoverPanels: '',
      deleteName: '',
      curDeleteData: {
        binded_modules: [],
      },
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
    deleteAlertTip() {
      return this.$t(
        '删除持久存储后无法恢复，目前有 {c} 个模块绑定了该存储，请确认影响',
        { c: this.curDeleteData.binded_modules.length },
      );
    },
    preReleaseEnvironment() {
      return this.createPersistentStorageData.stage === 'stag';
    },
  },
  watch: {
    deleteName(newVal) {
      if (newVal === this.appCode) {
        this.delteDialogConfig.isDisabled = false;
      }
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.getPersistentStorageList();
    },

    // 获取持久化存储列表
    async getPersistentStorageList() {
      this.isLoading = true;
      try {
        let res = await  this.$store.dispatch('persistentStorage/getPersistentStorageList', {
          appCode: this.appCode,
          sourceType: defaultSourceType,
        });

        if (res.length) {
          res = res.map((item) => {
            item.formatBindedModules = [];
            // binded_modules 二维数组
            if (item.binded_modules.length) {
              item.binded_modules.map((v) => {
                item.formatBindedModules.push({
                  module: v[0],
                  path: v[1],
                });
              });
            }
            item.isExpanded = false;
            return item;
          });
        }

        this.persistentStorageList = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        setTimeout(() => {
          this.isLoading = false;
        }, 200);
      }
    },
    handlerPanelChage(data) {
      data.isExpanded = !data.isExpanded;
    },
    // 新增持久存储
    handlerPersistentStorage() {
      this.storageDialogConfig.visible = true;
    },
    // 查看计费方式
    viewBillingMethod() {
      const url = 'https://cloud.tencent.com/document/product/582/47378';
      window.open(url, '_blank');
    },
    // 新建存储
    async handlerConfirm() {
      this.storageDialogConfig.isLoading = true;
      const data = {
        environment_name: this.createPersistentStorageData.stage,
        source_type: defaultSourceType,
        persistent_storage_source: {
          storage: this.createPersistentStorageData.capacity,
        },
      };
      try {
        await this.$store.dispatch('persistentStorage/createPersistentStorage', {
          appCode: this.appCode,
          data,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('新建成功！'),
        });
        this.handlerCancel();
        this.getPersistentStorageList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.storageDialogConfig.isLoading = false;
      }
    },
    // 新建存储数据重置
    handlerCancel() {
      this.storageDialogConfig.visible = false;
      setTimeout(() => {
        this.createPersistentStorageData = {
          stage: 'stag',
          capacity: '1Gi',
        };
      }, 500);
    },
    // 删除
    handlerDelete(data) {
      this.curDeleteData = data;
      this.delteDialogConfig.visible = true;
    },
    // 删除存储
    async deletePersistentStorage() {
      if (this.deleteName !== this.appCode) {
        return;
      }
      this.delteDialogConfig.isLoading = true;
      try {
        await this.$store.dispatch('persistentStorage/deletePersistentStorage', {
          appCode: this.appCode,
          sourceType: defaultSourceType,
          sourceName: this.curDeleteData.name,
        });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除成功！'),
        });
        this.handlerDeleteCancel();
        this.getPersistentStorageList();
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.delteDialogConfig.isLoading = false;
      }
    },
    //  取消删除
    handlerDeleteCancel() {
      this.delteDialogConfig.visible = false;
      setTimeout(() => {
        this.deleteName = '';
        this.delteDialogConfig.isDisabled = true;
        this.delteDialogConfig.isLoading = false;
      }, 500);
    },
  },
};
</script>

<style lang="scss" scoped>
.storage-container {
  padding: 24px;
  background: #ffffff;
  box-shadow: 0 2px 4px 0 #1919290d;
  border-radius: 2px;
  font-size: 12px;

  .top {
    i.plus {
      font-size: 12px;
      font-weight: 700;
    }
    .tips {
      i.tips-line {
        width: 14px;
        height: 14px;
        color: #979ba5;
      }
      span {
        color: #63656e;
      }
    }
  }

  .collapse-panel {
    .panel-item {
      position: relative;
      display: flex;
      align-items: center;
      margin-top: 16px;
      height: 64px;
      background: #fafbfd;
      border: 1px solid #dcdee5;
      border-radius: 2px;

      &:hover {
        cursor: pointer;
        background: #f5f7fa;
      }

      &.active {
        border-bottom: none;
        border-radius: 2px 2px 0 0;
      }

      .icon-warpper {
        width: 46px;
        text-align: center;
        line-height: 64px;
        i {
          color: #c4c6cc;
        }
      }
      .main {
        .name {
          line-height: 22px;
          font-weight: 700;
          font-size: 14px;
          color: #63656e;
        }
        .info span {
          color: #979ba5;
          line-height: 20px;

          &:not(:first-child) {
            margin-left: 35px;
          }
        }
      }
      .delete {
        transition: all 0.2s;
        font-size: 14px;
        color: #ea3636;
        position: absolute;
        padding: 4px;
        right: 20px;
        top: 50%;
        transform: translateY(-50%);
        cursor: pointer;
      }
    }
    .content {
      border: 1px solid #dcdee5;
      border-top: none;
    }
  }
  .exception-text {
    line-height: 22px;
    color: #979ba5;
    font-size: 12px;
  }
}
.storage-dialog-content {
  .bk-alert-content {
    font-size: 12px;
  }
  i.remind-cls {
    margin-right: 3px;
    font-size: 14px;
    color: #ea3636;
  }
  .capacity-tips {
    font-size: 12px;
    color: #979ba5;
  }
}
.del-storage-dialog-content {
    i.remind-cls {
      margin-right: 3px;
      font-size: 14px;
      color: #ea3636;
    }
    .delete-tips {
        margin-top: 16px;
        line-height: 22px;
    }
}
</style>
<style>
.store-module-table-cls .bk-table-header-wrapper .bk-table-header .has-gutter tr th {
  background-color: #f0f1f5;
}
.store-module-table-cls .bk-table-body .bk-table-row-last td {
  border-bottom: none;
}
.store-module-table-cls .bk-table-empty-block {
  height: 180px;
}
</style>
