<template>
  <bk-sideslider
    :is-show.sync="sidesliderVisible"
    :quick-close="true"
    width="640"
    show-mask
    ext-cls="members-sideslider-cls"
    @shown="handleShown"
    @hidden="handleHidden"
  >
    <div slot="header">
      <div class="header-box">
        <span>{{ title }}</span>
      </div>
    </div>
    <div
      class="sideslider-content-cls"
      ref="sideslider"
      slot="content"
    >
      <div :class="['sideslider-main', { view: isView }]">
        <bk-form
          :label-width="200"
          form-type="vertical"
          ref="formRef"
        >
          <template v-if="!isView">
            <bk-form-item
              :label="$t('用户名')"
              :required="true"
              :property="'name'"
            >
              <user
                v-model="formData.users"
                :multiple="true"
                :placeholder="$t('请输入用户名')"
                :empty-text="$t('无匹配人员')"
                :disabled="isEidt"
              />
            </bk-form-item>
            <bk-form-item
              :label="$t('角色')"
              :required="true"
            >
              <bk-radio-group v-model="formData.role">
                <bk-radio
                  v-for="item in roleList"
                  :value="item.id"
                  :key="item.id"
                >
                  {{ item.label }}
                </bk-radio>
              </bk-radio-group>
            </bk-form-item>
          </template>
          <bk-form-item :label="!isView ? $t('权限模型') : ''">
            <!-- 权限模型列表 -->
            <ul :class="['permission-list', `column-${formData.role}`]">
              <li class="role-titile">
                <div class="operate">{{ $t('操作') }}</div>
                <div
                  v-for="t in roleList"
                  :key="t.id"
                  class="header-column"
                >
                  {{ t.label }}
                </div>
              </li>
              <li
                v-for="(val, key) in PERMISSIONS"
                :class="['role-item', { 'is-last': '模块管理' === key }]"
              >
                <div
                  class="operate text-ellipsis"
                  v-bk-overflow-tips
                >
                  {{ $t(key) }}
                </div>
                <div
                  v-for="role in roleList"
                  :key="role.id"
                  :class="{ 'last-column': '模块管理' === key }"
                >
                  <i
                    class="paasng-icon paasng-correct"
                    v-if="val.includes(role.id)"
                  ></i>
                  <i
                    class="paasng-icon paasng-bold-close"
                    v-else
                  ></i>
                </div>
              </li>
            </ul>
          </bk-form-item>
        </bk-form>
        <!-- 权限描述 -->
        <ul class="permission-notes">
          <li>
            {{
              $t(
                '基础开发：包含部署管理、进程管理、日志查询、环境配置、访问入口、增强服务信息查看、代码库配置、镜像凭证等功能'
              )
            }}
          </li>
          <li>{{ $t('模块管理：包含设置为主模块、新建模块') }}</li>
          <li>{{ $t('增强服务管理：包含增强服务的解绑、删除等功能') }}</li>
        </ul>
      </div>
      <div
        v-if="!isView"
        slot="footer"
        class="footer-btns"
      >
        <bk-button
          :theme="'primary'"
          class="mr8"
          :loading="config.loading"
          @click="handleConfirm"
        >
          {{ $t('确定') }}
        </bk-button>
        <bk-button
          :theme="'default'"
          @click="handleCancel"
        >
          {{ $t('取消') }}
        </bk-button>
      </div>
    </div>
  </bk-sideslider>
</template>

<script>
import user from '@/components/user';
export default {
  name: 'MembersSideslider',
  components: {
    user,
  },
  props: {
    show: {
      type: Boolean,
      default: false,
    },
    data: {
      type: Object,
      default: () => ({}),
    },
    config: {
      type: Object,
      default: () => ({}),
    },
    title: {
      type: String,
      default: '',
    },
    type: {
      type: String,
      default: 'new',
    },
  },
  data() {
    return {
      formData: {
        users: [],
        role: 2,
      },
      // 角色列表
      roleList: [
        { id: 2, label: this.$t('管理员') },
        { id: 3, label: this.$t('开发者') },
        { id: 4, label: this.$t('运营者') },
      ],
      // 权限模型列表：2管理员、3开发者、4运营者
      PERMISSIONS: {
        基础信息查看: [2, 3, 4],
        数据统计: [2, 3, 4],
        告警记录: [2, 3, 4],
        应用推广: [2, 3, 4],
        基础开发: [2, 3],
        '云 API 管理': [2, 3],
        告警策略配置: [2, 3],
        基本信息编辑: [2, 4],
        权限管理: [2, 4],
        应用删除: [2],
        成员管理: [2],
        增强服务管理: [2],
        部署环境限制管理: [2],
        模块管理: [2],
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
    appCode() {
      return this.$route.params.id;
    },
    isEidt() {
      return this.config.type === 'edit';
    },
    isView() {
      return this.config.type === 'view';
    },
  },
  methods: {
    handleShown() {
      if (this.isEidt) {
        const { user, role = 2 } = this.config.row;
        this.formData.users = [user];
        this.formData.role = role;
      }
    },
    handleCancel() {
      this.sidesliderVisible = false;
    },
    handleHidden() {
      this.formData = {
        users: [],
        role: 2,
      };
    },
    // 确定
    handleConfirm() {
      const { users, role } = this.formData;
      if (!users.length) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('请选择成员！'),
        });
        return;
      }
      if (this.isEidt) {
        // 更换角色
        const updateParam = {
          role: {
            id: this.formData.role,
          },
        };
        this.$emit('confirm', updateParam, role);
        return;
      }
      // 新增成员
      const parmas = users.map((username) => ({
        application: { code: this.appCode },
        user: { username },
        roles: [{ id: role }],
      }));
      this.$emit('confirm', parmas, role);
    },
  },
};
</script>

<style lang="scss" scoped>
.header-box {
  .desc {
    height: 22px;
    margin-left: 10px;
    padding-left: 8px;
    font-size: 14px;
    color: #979ba5;
    border-left: 1px solid #dcdee5;
  }
}
.members-sideslider-cls {
  /deep/ .bk-sideslider-content {
    overflow: hidden;
    height: 100%;
    max-height: calc(100vh - 52px) !important;
  }
  .footer-btns {
    flex-shrink: 0;
    background: #fafbfd;
    box-shadow: 0 -1px 0 0 #dcdee5;
    z-index: 9;
    height: 48px;
    line-height: 48px;
    padding-left: 24px;
  }
}
.sideslider-content-cls {
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  .sideslider-main {
    flex: 1;
    overflow: auto;
    padding: 16px 40px;
    /* 查看模式 */
    &.view .permission-list {
      i.paasng-correct {
        color: #2caf5e !important;
      }
      .paasng-bold-close {
        color: #ea3636 !important;
      }
      li.role-item div,
      div.header-column {
        background: unset !important;
        border: none !important;
      }
    }
    .permission-list {
      font-size: 12px;
      color: #313238;
      /* 高亮样式 */
      @for $i from 2 through 4 {
        &.column-#{$i} li div:nth-child(#{$i}) {
          background: #f0f5ffb3;
          border-right: 1px solid #3a84ff;
          border-left: 1px solid #3a84ff;
          .paasng-correct {
            color: #2caf5e;
          }
          .paasng-bold-close {
            color: #ea3636;
          }
          &.last-column {
            border-bottom: 1px solid #3a84ff;
          }
          &.header-column {
            border-top: 1px solid #3a84ff;
          }
        }
      }
      li {
        display: flex;
        align-items: center;
        padding: 0 24px;
        height: 32px;
        line-height: 32px;
        &:nth-child(2n + 1) {
          background: #fafbfd;
        }
        &.role-titile {
          background: #f5f7fa;
        }
        &.operate {
          flex-shrink: 0;
          width: 180px;
        }
        div {
          flex: 1;
          i {
            color: #c4c6cc;
            font-size: 14px;
            &.paasng-correct {
              font-size: 20px;
            }
          }
          &:not(.operate) {
            text-align: center;
          }
        }
      }
    }
    .permission-notes {
      margin: 16px 0 0 7px;
      margin-top: 16px;
      font-size: 12px;
      color: #313238;
      li {
        position: relative;
        margin-bottom: 8px;
        &::before {
          content: '';
          position: absolute;
          left: -7px;
          top: 8px;
          width: 2px;
          height: 2px;
          border-radius: 50%;
          background: #4d4f56;
          transform: translateY(-50%);
        }
      }
    }
  }
}
</style>
