<template>
  <div class="right-main">
    <paas-content-loader
      class="app-container middle"
      :is-loading="isLoading"
      placeholder="persistent-storage-loading"
    >
      <section class="storage-container">
        <!-- 不支持持久存储 -->
        <section v-if="!isClusterPersistentStorageSupported">
          <FunctionalDependency
            mode="partial"
            :title="$t('暂无持久存储功能')"
            :functional-desc="
              $t(
                '开发者中心的持久存储功能为多个模块和进程提供了一个共享的数据源，实现了数据的共享与交互，并确保了数据在系统故障或重启后的持久化和完整性。'
              )
            "
            :guide-title="$t('如需使用该功能，需要：')"
            :guide-desc-list="[
              $t('1. 在应用集群创建 StorageClass 并注册到开发者中心'),
              $t('2. 给应用开启持久存储特性'),
            ]"
            @gotoMore="gotoMore"
          />
        </section>
        <template v-else>
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
                {{
                  $t(
                    '持久化存储使用腾讯云 CFS，可用于多个模块、进程间共享数据。持久存储申请后就会产生实际的费用，请按需申请，不用的资源请及时删除。'
                  )
                }}
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
                  {{
                    $t(
                      '持久化存储可用于多个模块、进程间共享数据。持久存储申请后就会产生资源成本，请按需申请，不用的资源请及时删除。'
                    )
                  }}
                </span>
              </span>
            </div>
            <!-- 存储列表 -->
            <section
              class="collapse-panel"
              v-for="item in persistentStorageList"
              :key="item.display_name"
            >
              <section
                :class="['panel-item', { active: item.isExpanded }]"
                @click="handlerPanelChage(item)"
                @mouseenter="curHoverPanels = item.display_name"
                @mouseleave="curHoverPanels = ''"
              >
                <div class="icon-warpper">
                  <i class="paasng-icon paasng-play-shape"></i>
                </div>
                <div class="main">
                  <p class="name">{{ item.display_name }}</p>
                  <div class="info">
                    <span>
                      {{ $t('生效环境') }}：{{ item.environment_name === 'stag' ? $t('预发布环境') : $t('生产环境') }}
                    </span>
                    <span>{{ $t('容量') }}：{{ persistentStorageSizeMap[item.storage_size] }}</span>
                    <span>{{ $t('已绑定模块数') }}：{{ item.bound_modules?.length || 0 }}</span>
                  </div>
                </div>
                <div
                  :class="['delete', { disabled: item.bound_modules?.length }]"
                  v-show="curHoverPanels === item.display_name"
                  v-bk-tooltips="{
                    content: $t(
                      '当前存在{n}个模块已绑定该持久存储。请先前往“模块配置”下的“挂载卷”页面，删除相关挂载项，之后才可以删除持久存储。',
                      { n: item.bound_modules?.length }
                    ),
                    disabled: !item.bound_modules?.length,
                  }"
                  @click.stop="handlerDelete(item)"
                >
                  <i class="paasng-icon paasng-delete"></i>
                  {{ $t('删除') }}
                </div>
              </section>
              <section
                class="content"
                v-if="item.isExpanded"
              >
                <bk-table
                  v-if="item.bound_modules?.length"
                  :data="item.bound_modules"
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
                <bk-exception
                  v-else
                  type="empty"
                  scene="part"
                >
                  <p class="mt10 exception-text">{{ $t('暂无数据') }}</p>
                  <p class="exception-text">
                    {{ $t('您可在“模块配置-挂载卷”页面将持久存储挂载到指定模块的指定目录中') }}
                  </p>
                </bk-exception>
              </section>
            </section>
          </template>
        </template>
      </section>

      <!-- 新增持久存储 -->
      <create-persistent-storage-dailog
        v-model="persistentStorageDailogVisible"
        @get-list="getPersistentStorageList"
      />

      <!-- 删除持久存储 -->
      <bk-dialog
        v-model="delteDialogConfig.visible"
        theme="primary"
        :width="640"
        :mask-close="false"
        :title="`${$t('删除持久存储')} ${curDeleteData.display_name}`"
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
          <bk-alert type="error">
            <div slot="title">
              {{ $t('删除持久存储后无法恢复，请确认影响') }}
            </div>
          </bk-alert>
          <div class="delete-tips spacing-x1">
            {{ $t('请完整输入') }}
            <code>{{ appCode }}</code>
            {{ $t('来确认删除存储！') }}
          </div>
          <bk-input v-model="deleteName"></bk-input>
        </section>
      </bk-dialog>
    </paas-content-loader>
  </div>
</template>

<script>
import createPersistentStorageDailog from '@/components/create-persistent-storage-dailog';
import FunctionalDependency from '@blueking/functional-dependency/vue2/index.umd.min.js';
import { PERSISTENT_STORAGE_SIZE_MAP } from '@/common/constants';

const defaultSourceType = 'PersistentStorage';

export default {
  name: 'AppPersistentStorage',
  components: {
    createPersistentStorageDailog,
    FunctionalDependency,
  },
  data() {
    return {
      isLoading: true,
      persistentStorageList: [],
      delteDialogConfig: {
        visible: false,
        isLoading: false,
        isDisabled: true,
      },
      curHoverPanels: '',
      deleteName: '',
      curDeleteData: {
        bound_modules: [],
      },
      persistentStorageDailogVisible: false,
      isClusterPersistentStorageSupported: false,
      persistentStorageSizeMap: PERSISTENT_STORAGE_SIZE_MAP,
    };
  },
  computed: {
    appCode() {
      return this.$route.params.id;
    },
    localLanguage() {
      return this.$store.state.localLanguage;
    },
  },
  watch: {
    deleteName(newVal) {
      if (newVal === this.appCode) {
        this.delteDialogConfig.isDisabled = false;
      }
    },
    $route() {
      this.init();
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.isLoading = true;
      Promise.all([this.getClusterPersistentStorageFeature(), this.getPersistentStorageList()]).finally(() => {
        this.isLoading = false;
      });
    },

    // 获取持久化存储列表
    async getPersistentStorageList() {
      try {
        let res = await this.$store.dispatch('persistentStorage/getPersistentStorageList', {
          appCode: this.appCode,
          sourceType: defaultSourceType,
        });

        if (res.length) {
          res = res.map((item) => {
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
      }
    },
    handlerPanelChage(data) {
      data.isExpanded = !data.isExpanded;
    },
    // 新增持久存储
    handlerPersistentStorage() {
      this.persistentStorageDailogVisible = true;
    },
    // 删除
    handlerDelete(data) {
      if (data.bound_modules?.length) return;
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
    // 获取集群特性
    async getClusterPersistentStorageFeature() {
      try {
        const res = await this.$store.dispatch('persistentStorage/getClusterPersistentStorageFeature', {
          appCode: this.appCode,
        });
        this.isClusterPersistentStorageSupported = res;
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
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
    gotoMore() {
      const baseDocUrl = this.GLOBAL.LINK.BK_APP_DOC?.endsWith('/')
        ? this.GLOBAL.LINK.BK_APP_DOC
        : `${this.GLOBAL.LINK.BK_APP_DOC}/`;
      const docUrl = `${baseDocUrl}topics/paas/paas_persistent_storage`;
      window.open(docUrl, '_blank');
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
        font-size: 14px;
        color: #979ba5;
        transform: translateY(0);
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

        &.disabled {
          color: #c4c6cc;
          cursor: not-allowed;
        }
      }
    }
    .content {
      border: 1px solid #dcdee5;
      border-top: none;

      .bk-exception {
        height: 180px;
      }
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
</style>
