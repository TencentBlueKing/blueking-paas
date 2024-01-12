<template lang="html">
  <div class="right-main">
    <paas-plugin-title />
    <paas-content-loader
      class="app-container"
      :is-loading="loading"
      placeholder="roles-loading"
      :is-transform="false"
    >
      <div class="plugin-deploy-wrapper card-style">
        <div class="ps-top-card mb15">
          <p class="main-title">
            {{ $t(configurationSchema.title) }}
          </p>
          <p class="desc">
            {{ $t(configurationSchema.description) }}
          </p>
        </div>
        <table
          v-bkloading="{ isLoading: isVarLoading, zIndex: 10 }"
          class="ps-table ps-table-default ps-table-width-overflowed"
          style="margin-bottom: 24px;"
        >
          <tr
            v-for="(varItem, index) in envVarList"
            :key="index"
          >
            <td>
              <bk-form
                :ref="varItem.key"
                form-type="inline"
                :model="varItem"
              >
                <bk-form-item
                  :rules="varRules.key"
                  :property="'key'"
                  style="flex: 1 1 25%;"
                >
                  <bk-input
                    v-model="varItem.key"
                    placeholder="KEY"
                    :clearable="false"
                    :readonly="isReadOnlyRow(index)"
                  />
                </bk-form-item>
                <bk-form-item
                  :rules="varRules.value"
                  :property="'value'"
                  style="flex: 1 1 25%;"
                >
                  <template v-if="isReadOnlyRow(index)">
                    <div
                      v-bk-tooltips="{ content: varItem.value, trigger: 'mouseenter', maxWidth: 400, extCls: 'env-var-popover' }"
                      class="desc-form-content"
                    >
                      {{ varItem.value }}
                    </div>
                  </template>
                  <template v-else>
                    <bk-input
                      v-model="varItem.value"
                      placeholder="VALUE"
                      :clearable="false"
                      :readonly="isReadOnlyRow(index)"
                    />
                  </template>
                </bk-form-item>
                <bk-form-item
                  :rules="varRules.description"
                  :property="'description'"
                  style="flex: 1 1 25%;"
                >
                  <template v-if="isReadOnlyRow(index)">
                    <div
                      v-if="varItem.description !== ''"
                      v-bk-tooltips="{ content: varItem.description, trigger: 'mouseenter', maxWidth: 400, extCls: 'env-var-popover' }"
                      class="desc-form-content"
                    >
                      {{ varItem.description }}
                    </div>
                    <div
                      v-else
                      class="desc-form-content"
                    >
                      {{ varItem.description }}
                    </div>
                  </template>
                  <template v-else>
                    <bk-input
                      v-model="varItem.description"
                      :placeholder="$t('描述')"
                      :clearable="false"
                    />
                  </template>
                </bk-form-item>
                <bk-form-item style="flex: 1 1 7%; padding-left: 10px; min-width: 80px;">
                  <template v-if="isReadOnlyRow(index)">
                    <a
                      class="paasng-icon paasng-edit ps-btn ps-btn-icon-only btn-ms-primary"
                      @click="editingRowToggle({}, index)"
                    />
                    <tooltip-confirm
                      ref="deleteTooltip"
                      :ok-text="$t('确定')"
                      :cancel-text="$t('取消')"
                      :theme="'ps-tooltip'"
                      @ok="deleteConfigVar(varItem.__id__)"
                    >
                      <a
                        v-show="isReadOnlyRow(index)"
                        slot="trigger"
                        class="paasng-icon paasng-delete ps-btn ps-btn-icon-only btn-ms-primary"
                      />
                    </tooltip-confirm>
                  </template>
                  <template v-else>
                    <a
                      class="paasng-icon paasng-check-1 ps-btn ps-btn-icon-only"
                      type="submit"
                      @click="updateConfigVar(varItem.__id__, index, varItem)"
                    />
                    <a
                      class="paasng-icon paasng-close ps-btn ps-btn-icon-only"
                      style="margin-left: 0;"
                      @click="editingRowToggle(varItem, index, 'cancel')"
                    />
                  </template>
                </bk-form-item>
              </bk-form>
            </td>
          </tr>
          <tr>
            <td>
              <bk-form
                ref="newVarForm"
                form-type="inline"
                :model="newVarConfig"
              >
                <bk-form-item
                  :rules="varRules.key"
                  :property="'key'"
                  style="flex: 1 1 25%;"
                >
                  <bk-input
                    v-model="newVarConfig.key"
                    placeholder="KEY"
                    :clearable="false"
                  />
                </bk-form-item>
                <bk-form-item
                  :rules="varRules.value"
                  :property="'value'"
                  style="flex: 1 1 25%;"
                >
                  <bk-input
                    v-model="newVarConfig.value"
                    placeholder="VALUE"
                    :clearable="false"
                  />
                </bk-form-item>
                <bk-form-item
                  :rules="varRules.description"
                  :property="'description'"
                  style="flex: 1 1 25%;"
                >
                  <bk-input
                    v-model="newVarConfig.description"
                    :placeholder="$t('描述')"
                    :clearable="false"
                  />
                </bk-form-item>
                <bk-form-item style="flex: 1 1 7%; padding-left: 10px; min-width: 80px;">
                  <bk-button
                    theme="primary"
                    :outline="true"
                    @click.stop.prevent="verifyVarForm"
                  >
                    {{ $t('添加') }}
                  </bk-button>
                </bk-form-item>
              </bk-form>
            </td>
          </tr>
        </table>
      </div>
    </paas-content-loader>
  </div>
</template>

<script>
import _ from 'lodash';
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
import tooltipConfirm from '@/components/ui/TooltipConfirm';
import paasPluginTitle from '@/components/pass-plugin-title';

export default {
  components: {
    tooltipConfirm,
    paasPluginTitle,
  },
  mixins: [pluginBaseMixin],
  data() {
    return {
      loading: true,
      isVarLoading: true,
      envVarList: [],
      envVarListBackup: [],
      configurationSchema: {},
      newVarConfig: {
        key: '',
        value: '',
        description: '',
      },
      editRowList: [],
      varRules: {
        key: [
          {
            required: true,
            message: this.$t('KEY是必填项'),
            trigger: 'blur',
          },
          {
            max: 64,
            message: this.$t('不能超过64个字符'),
            trigger: 'blur change',
          },
          {
            regex: /^[A-Z][A-Z0-9_]*$/,
            message: this.$t('只能以大写字母开头，仅包含大写字母、数字与下划线'),
            trigger: 'blur change',
          },
        ],
        value: [
          {
            required: true,
            message: this.$t('VALUE是必填项'),
            trigger: 'blur',
          },
          {
            max: 2048,
            message: this.$t('不能超过2048个字符'),
            trigger: 'blur change',
          },
        ],
        description: [
          {
            validator: (value) => {
              if (value === '') {
                return true;
              }
              return value.trim().length <= 200;
            },
            message: this.$t('不能超过200个字符'),
            trigger: 'blur',
          },
        ],
      },
    };
  },
  watch: {
    '$route'() {
      this.init();
    },
  },
  created() {
    this.init();
  },
  methods: {
    init() {
      this.getConfigurationSchema();
      this.getEnvVarList();
    },

    isReadOnlyRow(rowIndex) {
      return !_.includes(this.editRowList, rowIndex);
    },

    async getConfigurationSchema() {
      try {
        const { pdId } = this;
        const res = await this.$store.dispatch('plugin/getConfigurationSchema', { pdId });
        this.configurationSchema = res;
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      }
    },

    async getEnvVarList() {
      this.isVarLoading = true;
      try {
        const { pdId } = this;
        const { pluginId } = this;
        const res = await this.$store.dispatch('plugin/getEnvVarList', { pdId, pluginId });
        this.envVarList = res;
        this.envVarListBackup = JSON.parse(JSON.stringify(this.envVarList));
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.isVarLoading = false;
        this.loading = false;
      }
    },

    verifyVarForm() {
      this.$refs.newVarForm.validate().then(() => {
        this.createConfigVar();
      })
        .catch((e) => {
          console.error(e);
        });
    },

    async createConfigVar() {
      const createForm = {
        key: this.newVarConfig.key,
        value: this.newVarConfig.value,
        description: this.newVarConfig.description,
      };
      try {
        const { pdId } = this;
        const { pluginId } = this;
        await this.$store.dispatch('plugin/editEnvVar', { pdId, pluginId, data: createForm });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('添加环境变量成功'),
        });
        this.newVarConfig = {
          key: '',
          value: '',
          description: '',
        };
        this.getEnvVarList();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: `${this.$t('添加环境变量失败')}，${e.message}`,
        });
      }
    },

    editingRowToggle(rowItem = {}, rowIndex, type = '') {
      if (type === 'cancel') {
        const currentItem = this.envVarListBackup.find(envItem => envItem.__id__ === rowItem.__id__);
        rowItem = currentItem;
        if (this.$refs[`${rowItem.key}`] && this.$refs[`${rowItem.key}`].length) {
          this.$refs[`${rowItem.key}`][0].formItems.forEach((item) => {
            item.validator.content = '';
            item.validator.state = '';
          });
        }
      }
      if (_.includes(this.editRowList, rowIndex)) {
        this.editRowList.pop(rowIndex);
      } else {
        this.editRowList.push(rowIndex);
      }
    },

    // 更新环境变量
    async updateConfigVar(configVarID, index, varItem) {
      const curRef = varItem.key;
      this.$refs[curRef][0].validate().then(async () => {
        const editForm = varItem;
        try {
          const { pdId } = this;
          const { pluginId } = this;
          await this.$store.dispatch('plugin/editEnvVar', { pdId, pluginId, data: editForm });
          this.$paasMessage({
            theme: 'success',
            message: this.$t('修改环境变量成功'),
          });
          this.getEnvVarList();
          this.editingRowToggle(varItem, index, 'cancel');
        } catch (e) {
          this.$bkMessage({
            theme: 'error',
            message: `${this.$t('修改环境变量失败')}，${e.message}`,
          });
        }
      });
    },

    // 删除环境变量
    async deleteConfigVar(configVarID) {
      try {
        const { pdId } = this;
        const { pluginId } = this;
        await this.$store.dispatch('plugin/deleteEnvVar', { pdId, pluginId, configId: configVarID });
        this.$paasMessage({
          theme: 'success',
          message: this.$t('删除环境变量成功'),
        });
        this.getEnvVarList();
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: `${this.$t('删除环境变量失败')}，${e.message}`,
        });
      }
    },
  },
};
</script>

<style lang="scss" scoped>
    .content-wrapper {
        margin-top: 16px;
    }
    .search-input {
         width: 360px;
         display: inline-block;
    }
    .user-photo {
        margin: 5px 0;
        display: inline-block;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        overflow: hidden;
        border: solid 1px #eaeaea;
        vertical-align: middle;

        img {
            width: 100%;
            height: 100%;
        }
    }

    .user-name {
        display: inline-block;
        padding-left: 10px;
        font-size: 14px;
        color: #333;
        vertical-align: middle;
    }

    .ps-pr {
        padding-right: 15px;
        color: #999;
    }

    .ps-table-width-overflowed {
        width: 100%;
        margin-left: 0;

        td {
            border-bottom: 0;
            padding: 15px 0 0 0;
        }

        /deep/ .bk-form-content {
            width: 100%;
        }

        .desc-form-content {
            display: inline-block;
            padding: 0 10px;
            width: 100%;
            height: 32px;
            border: 1px solid #dcdee5;
            border-radius: 2px;
            text-align: left;
            font-size: 12px;
            color: #63656e;
            overflow: hidden;
            background-color: #fafbfd;
            vertical-align: middle;
            cursor: default;
        }
        .bk-inline-form {
            display: flex;
        }
    }
    .variable-main {
        border-bottom: 0;

        h3 {
            line-height: 1;
            padding: 10px 0;
        }

        .ps-alert-content {
            color: #666;
        }
    }

    .variable-input {
        margin-right: 10px;

        input {
            height: 36px;
        }
    }
    .plugin-deploy-wrapper {
        padding: 24px;
    }
</style>

<style lang="scss">
    .right-main .plugin-deploy-wrapper .ps-table-default .bk-form .bk-form-item .bk-form-content {
        width: 100%;
        float: none !important;
        display: block !important;
    }
</style>
