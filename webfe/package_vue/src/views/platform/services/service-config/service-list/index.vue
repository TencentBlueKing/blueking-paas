<template>
  <div class="service-list">
    <section
      class="custom-service-loader"
      v-if="isLoading"
    >
      <div
        v-for="i in 8"
        :key="i"
        class="loader-item"
      ></div>
    </section>
    <template v-else>
      <div
        v-for="(service, key) in groupedServices"
        :key="key"
        :class="['group-items', key, { close: !expand[key] }]"
        v-bkloading="{ isLoading: isListLoading, zIndex: 10 }"
      >
        <div
          class="group-title"
          @click="toggleExpand(key)"
        >
          <div class="tiitle-content">
            <i
              class="paasng-icon paasng-left-shape"
              :class="{ expand: expand[key] }"
            ></i>
            {{ key === 'local' ? $t('本地增强服务') : $t('远程增强服务') }}
            <span class="count">（{{ service.length || 0 }}）</span>
          </div>
          <!-- 新增服务 -->
          <i
            v-bk-tooltips="$t('新增服务')"
            class="paasng-icon paasng-plus-thick"
            v-if="key === 'local'"
            @click.stop="showSideslider({}, 'new')"
          ></i>
        </div>
        <template v-if="expand[key]">
          <div
            v-for="item in service"
            :key="item.id"
            class="list-item"
            :class="{ active: selectedItem === item.uuid, 'not-visible': !item.is_visible }"
            @click="handleSelected(item)"
          >
            <!-- 左侧图标区域 -->
            <div class="logo-wrapper">
              <img
                class="logo"
                :src="item.logo"
              />
            </div>
            <!-- 中间内容区域 -->
            <div class="content">
              <div class="title">
                <div
                  class="text"
                  v-bk-overflow-tips
                >
                  {{ item.display_name }}
                  <span class="short-name">({{ item.name }})</span>
                </div>
                <div class="icon-wrapper">
                  <i
                    class="paasng-icon paasng-edit-2"
                    @click.stop="showSideslider(item, 'edit')"
                  ></i>
                  <i
                    v-if="key === 'local'"
                    class="paasng-icon paasng-bold-close"
                    @click.stop="deleteService(item)"
                  ></i>
                </div>
              </div>
              <!-- tag -->
              <div class="tag-list">
                <span
                  class="tag"
                  v-if="item.category_id === 1"
                >
                  {{ $t('数据存储') }}
                </span>
                <span
                  class="tag"
                  v-else-if="item.category_id === 2"
                >
                  {{ $t('监控检测') }}
                </span>
                <span
                  class="tag"
                  v-if="item.provider_name === 'pool'"
                >
                  {{ $t('资源池') }}
                </span>
                <span
                  class="tag"
                  v-if="!item.is_visible"
                >
                  {{ $t('不可见') }}
                </span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </template>

    <CreateEditSideslider
      :show.sync="sidesliderConfig.isShow"
      :type="sidesliderConfig.type"
      :data="sidesliderConfig.row"
      @refresh="getPlatformServices"
    />
  </div>
</template>

<script>
import CreateEditSideslider from './create-edit-sideslider.vue';
export default {
  components: {
    CreateEditSideslider,
  },
  props: {
    isInit: {
      type: Boolean,
      default: true,
    },
  },
  data() {
    return {
      // 所有服务
      services: [],
      isLoading: true,
      isListLoading: false,
      selectedItem: '', // 当前选中项
      expand: {
        local: true,
        remote: true,
      },
      sidesliderConfig: {
        isShow: false,
        type: 'new',
        row: {},
      },
    };
  },
  computed: {
    oldSelectedItem() {
      return this.$store.state.tenant.selectedServiceItem;
    },
    groupedServices() {
      const local = [];
      const remote = [];
      this.services.forEach((item) => {
        if (item.origin === 'local') {
          local.push(item);
        } else {
          remote.push(item);
        }
      });

      // 排序函数（is_visible优先，name次级）
      const sortByVisibilityAndName = (a, b) => {
        if (b.is_visible !== a.is_visible) {
          return b.is_visible - a.is_visible;
        }
        return a.name.localeCompare(b.name);
      };

      return {
        remote: [...remote].sort(sortByVisibilityAndName),
        local: [...local].sort(sortByVisibilityAndName),
      };
    },
  },
  watch: {
    isInit: {
      handler(newVal) {
        // 服务配置-租户接口响应后再获取服务
        if (newVal) {
          this.getPlatformServices();
        }
      },
      immediate: true,
    },
  },
  methods: {
    // 服务切换
    handleSelected(item) {
      if (this.selectedItem === item.uuid) return;
      this.selectedItem = item.uuid;
      this.$emit('change', item);
      this.$store.commit('tenant/updateSelectedServiceItem', item.uuid);
    },
    toggleExpand(group) {
      this.expand[group] = !this.expand[group];
    },
    // 获取服务列表
    async getPlatformServices() {
      this.isListLoading = true;
      try {
        const res = await this.$store.dispatch('tenant/getPlatformServices');
        this.services = res || [];
        this.$nextTick(() => {
          let activeItem = null;
          if (this.oldSelectedItem) {
            activeItem = res.find((item) => item.uuid === this.oldSelectedItem);
          }
          if (!activeItem) {
            activeItem = this.groupedServices?.remote[0] || res[0];
          }
          this.handleSelected(activeItem);
        });
        // 无远程服务收起
        if (!res.find((s) => s.origin === 'remote')) {
          this.expand.remote = false;
        }
      } catch (e) {
        this.catchErrorHandler(e);
      } finally {
        this.isLoading = false;
        this.isListLoading = false;
      }
    },
    // 编辑服务
    showSideslider(row, type) {
      this.sidesliderConfig.isShow = true;
      this.sidesliderConfig.type = type;
      this.sidesliderConfig.row = row;
    },
    // 删除服务
    async deleteService(row) {
      this.$bkInfo({
        confirmLoading: true,
        title: `${this.$t('确认删除服务')} ${row.name} ？`,
        confirmFn: async () => {
          try {
            await this.$store.dispatch('tenant/deletePlatformService', { serviceId: row.uuid });
            this.$paasMessage({
              theme: 'success',
              message: this.$t('删除成功'),
            });
            this.getPlatformServices();
            return true;
          } catch (e) {
            this.catchErrorHandler(e);
            return false;
          }
        },
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.service-list {
  height: 100%;
  overflow: auto;
  padding: 12px;
  flex-shrink: 0;
  width: 280px;
  .custom-service-loader {
    .loader-item {
      height: 56px;
      margin-bottom: 8px;
      background-color: #fff;
    }
  }

  .group-items.local.close {
    position: sticky;
    bottom: 0;
  }

  .group-title {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 10px;
    height: 40px;
    margin-bottom: 8px;
    background: #dcdee5;
    border-radius: 4px;
    color: #313238;
    font-weight: 500;
    cursor: pointer;
    i {
      cursor: pointer;
    }
    i.paasng-left-shape {
      margin-right: 6px;
      transform: rotate(-180deg) translateY(2px);
      &.expand {
        transform: rotate(-90deg) translateX(2px);
      }
    }
    i.paasng-plus-thick:hover {
      color: #3a84ff;
    }
  }

  .list-item {
    position: relative;
    display: flex;
    align-items: center;
    gap: 6px;
    height: 56px;
    padding: 8px;
    margin-bottom: 8px;
    background: #fff;
    box-shadow: 0 1px 3px 0 #0000001a;
    border-radius: 4px;
    cursor: pointer;
    user-select: none;
    .icon-wrapper {
      flex-shrink: 0;
      font-size: 12px;
      i {
        display: none;
      }
      i:hover {
        cursor: pointer;
        color: #3a84ff;
      }
      .paasng-edit-2 {
        transform: translateY(-2px);
      }
      .paasng-bold-close {
        margin-left: 5px;
        font-size: 16px;
      }
    }
    &.active {
      border: 1px solid #3a84ff;
      background: #f0f5ff;
      .tag-list {
        opacity: 1 !important;
        .tag {
          background: #fff;
        }
      }
      .logo-wrapper {
        background: #fff;
      }
    }
    &.not-visible {
      .title {
        color: #979ba5;
        .short-name {
          color: #dcdee5;
        }
      }
      .tag-list {
        opacity: 0.5;
      }
    }
    &:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      .icon-wrapper i {
        display: inline-block;
      }
    }
    .logo-wrapper {
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      background: #f5f7fa;
      border-radius: 2px;
      .logo {
        width: 24px;
        height: 24px;
        display: block;
      }
    }

    .content {
      flex: 1;
      overflow: hidden;
    }

    .title {
      display: flex;
      font-weight: 700;
      font-size: 14px;
      color: #313238;
      line-height: 22px;
      .text {
        min-width: 0;
        flex: 1;
        text-overflow: ellipsis;
        overflow: hidden;
        white-space: nowrap;
      }
      .short-name {
        font-size: 12px;
        color: #979ba5;
      }
    }

    .tag-list {
      .tag {
        height: 16px;
        line-height: 16px;
        padding: 0 4px;
        margin-right: 4px;
        font-size: 10px !important;
        &:last-child {
          margin-right: 0;
        }
      }
    }
  }
}
</style>
