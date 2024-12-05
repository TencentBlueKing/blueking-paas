<template>
  <div class="right-main paas-docu-manager-wrapper">
    <div class="ps-top-bar">
      <h2>
        {{ $t('文档管理') }}
        <a
          v-if="GLOBAL.DOC.PROJECT_MANAGER_GUIDE"
          class="link fr"
          :href="GLOBAL.DOC.PROJECT_MANAGER_GUIDE"
          target="_blank"
        > {{ $t('蓝鲸 SaaS 研发管理参考规范') }} </a>
      </h2>
    </div>
    <paas-content-loader
      class="app-container middle docu-container"
      :is-loading="isLoading"
      placeholder="docu-manager-loading"
    >
      <div v-if="!isLoading && tableList.length > 0">
        <bk-alert
          type="warning"
          :title="curTitle"
        />
        <table class="bk-table docu-manager-custom-table">
          <colgroup>
            <col style="width: 200px;">
            <col style="width: 200px;">
            <col style="width: 100px;">
            <col style="width: 250px;">
            <col style="width: 100px;">
            <col>
            <col style="width: 102px;">
          </colgroup>
          <thead>
            <th> {{ $t('文档分类') }} </th>
            <th> {{ $t('文档细项') }} </th>
            <th> {{ $t('是否使用') }} </th>
            <th> {{ $t('详细信息') }} </th>
            <th> {{ $t('更新人') }} </th>
            <th> {{ $t('更新时间') }} </th>
            <th> {{ $t('操作') }} </th>
          </thead>
          <tbody style="background: #fff;">
            <template v-for="row in tableList">
              <template v-if="row.children.length < 1">
                <tr :key="row.id">
                  <td>
                    <span
                      v-bk-tooltips.top="row.name"
                      class="name"
                    >{{ row.name }}</span>
                    <i
                      v-if="row.is_required"
                      class="is-required"
                    >*</i>
                  </td>
                  <td>--</td>
                  <td>
                    <template v-if="!row.isEdit">
                      <span :class="row.instance.is_used ? 'active' : ''">{{ row.instance.is_used ? $t('是') : $t('否') }}</span>
                    </template>
                    <template v-else>
                      <bk-switcher
                        :value="row.instance.is_used"
                        theme="primary"
                        @change="handleSwitchChange(...arguments, row)"
                      />
                    </template>
                  </td>
                  <td class="url-td">
                    <template v-if="row.instance.is_used && row.is_required && !row.instance.url && !row.isEdit">
                      <span>
                        <i
                          class="paasng-icon paasng-exclamation-circle"
                          style="color: #ffb848;"
                        />
                        {{ $t('请填写') }}
                      </span>
                    </template>
                    <template v-else>
                      <template v-if="!!row.instance.url">
                        <div v-if="!row.isEdit">
                          <bk-popconfirm
                            trigger="mouseenter"
                            ext-cls=""
                            confirm-button-is-text
                            :confirm-text="$t('复制')"
                            cancel-text=""
                            @confirm="handleCopy(row)"
                          >
                            <div slot="content">
                              {{ row.instance.url }}
                            </div>
                            <span style="display: inline-block; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                              {{ row.instance.url }}
                            </span>
                          </bk-popconfirm>
                        </div>
                        <template v-if="row.isEdit">
                          <bk-input
                            type="textarea"
                            :value="row.instance.url"
                            @input="handleUrlInput(...arguments, row)"
                          />
                        </template>
                      </template>
                      <template v-else>
                        <span v-if="!row.isEdit">--</span>
                        <template v-else>
                          <bk-input
                            type="textarea"
                            :value="row.instance.url"
                            @input="handleUrlInput(...arguments, row)"
                          />
                        </template>
                      </template>
                    </template>
                  </td>
                  <td>
                    {{ row.instance ? row.instance.latest_operator || '--' : '--' }}
                  </td>
                  <td>
                    {{ row.instance ? row.instance.updated ? smartTime(row.instance.updated, 'fromNow') : '--' : '--' }}
                  </td>
                  <td>
                    <template v-if="!row.isEdit">
                      <bk-button
                        theme="primary"
                        text
                        @click.native.stop
                        @click="handleEdit(row)"
                      >
                        {{ $t('编辑') }}
                      </bk-button>
                    </template>
                    <template v-else>
                      <bk-button
                        theme="primary"
                        text
                        @click.stop="handleSave(row)"
                      >
                        {{ $t('保存') }}
                      </bk-button>
                      <bk-button
                        style="margin-left: 5px;"
                        theme="primary"
                        text
                        @click.stop="handleCancel(row)"
                      >
                        {{ $t('取消') }}
                      </bk-button>
                    </template>
                  </td>
                </tr>
              </template>
              <template v-else>
                <tr :key="row.id">
                  <td>
                    <span
                      v-bk-tooltips.top="row.name"
                      class="name"
                    >{{ row.name }}</span>
                    <i
                      v-if="row.is_required"
                      class="is-required"
                    >*</i>
                  </td>
                  <td
                    colspan="6"
                    class="children-td"
                  >
                    <table class="bk-table sub-table">
                      <colgroup>
                        <col style="width: 200px;">
                        <col style="width: 100px;">
                        <col style="width: 250px;">
                        <col style="width: 100px;">
                        <col>
                        <col style="width: 102px;">
                      </colgroup>
                      <template v-for="subRow in row.children">
                        <tr :key="subRow.id">
                          <td>
                            <span
                              v-bk-tooltips.top="subRow.name"
                              class="name"
                            >{{ subRow.name }}</span>
                            <i
                              v-if="subRow.is_required"
                              class="is-required"
                            >*</i>
                          </td>
                          <td>
                            <template v-if="!subRow.isEdit">
                              <span :class="subRow.instance.is_used ? 'active' : ''">{{ subRow.instance.is_used ? $t('是') : $t('否') }}</span>
                            </template>
                            <template v-else>
                              <bk-switcher
                                :value="subRow.instance.is_used"
                                theme="primary"
                                @change="handleSwitchChange(...arguments, subRow)"
                              />
                            </template>
                          </td>
                          <td class="url-td">
                            <template v-if="subRow.instance.is_used && subRow.is_required && !subRow.instance.url && !subRow.isEdit">
                              <span>
                                <i
                                  class="paasng-icon paasng-exclamation-circle"
                                  style="color: #ffb848;"
                                />
                                {{ $t('请填写') }}
                              </span>
                            </template>
                            <template v-else>
                              <template v-if="!!subRow.instance.url">
                                <div v-if="!subRow.isEdit">
                                  <bk-popconfirm
                                    trigger="mouseenter"
                                    ext-cls=""
                                    confirm-button-is-text
                                    confirm-text="复制"
                                    cancel-text=""
                                    @confirm="handleCopy(subRow)"
                                  >
                                    <div slot="content">
                                      {{ subRow.instance.url }}
                                    </div>
                                    <span style="display: inline-block; max-width: 220px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap">
                                      {{ subRow.instance.url }}
                                    </span>
                                  </bk-popconfirm>
                                </div>
                                <template v-if="subRow.isEdit">
                                  <bk-input
                                    type="textarea"
                                    :value="subRow.instance.url"
                                    @input="handleUrlInput(...arguments, subRow)"
                                  />
                                </template>
                              </template>
                              <template v-else>
                                <span v-if="!subRow.isEdit">--</span>
                                <template v-else>
                                  <bk-input
                                    type="textarea"
                                    :value="subRow.instance.url"
                                    @input="handleUrlInput(...arguments, subRow)"
                                  />
                                </template>
                              </template>
                            </template>
                          </td>
                          <td
                            v-bk-overflow-tips
                            class="text-ellipsis"
                          >
                            {{ subRow.instance ? subRow.instance.latest_operator || '--' : '--' }}
                          </td>
                          <td
                            v-bk-overflow-tips
                            class="text-ellipsis"
                          >
                            {{ subRow.instance ? subRow.instance.updated ? smartTime(subRow.instance.updated, 'fromNow') : '--' : '--' }}
                          </td>
                          <td>
                            <template v-if="!subRow.isEdit">
                              <bk-button
                                theme="primary"
                                text
                                @click.native.stop
                                @click="handleEdit(subRow)"
                              >
                                {{ $t('编辑') }}
                              </bk-button>
                            </template>
                            <template v-else>
                              <bk-button
                                theme="primary"
                                text
                                @click.stop="handleSave(subRow)"
                              >
                                {{ $t('保存') }}
                              </bk-button>
                              <bk-button
                                style="margin-left: 5px;"
                                theme="primary"
                                text
                                @click.stop="handleCancel(subRow)"
                              >
                                {{ $t('取消') }}
                              </bk-button>
                            </template>
                          </td>
                        </tr>
                      </template>
                    </table>
                  </td>
                </tr>
              </template>
            </template>
          </tbody>
        </table>
      </div>
      <div
        v-if="!isLoading && tableList.length < 1"
        class="empty-wrapper"
      >
        <table-empty empty />
      </div>
    </paas-content-loader>
  </div>
</template>
<script>import appBaseMixin from '@/mixins/app-base-mixin';

export default {
  name: 'PaasDocuManager',
  mixins: [appBaseMixin],
  data() {
    return {
      isLoading: false,
      notCompletedCount: 0,
      tableList: [],
    };
  },
  computed: {
    curTitle() {
      return `${this.$t('文档中有')} ${this.notCompletedCount} ${this.$t('项必填未填写，请继续完善。')}`;
    },
  },
  watch: {
    '$route'() {
      this.notCompletedCount = 0;
      this.fetchData();
    },
  },
  created() {
    this.fetchData();
  },
  methods: {
    async fetchData() {
      this.isLoading = true;
      try {
        const res = await this.$store.dispatch('docuManagement/getDocumentInstance', {
          appCode: this.curAppCode,
        });
        const docuList = JSON.parse(JSON.stringify(res));
        const childrenList = [];
        let count = 0;
        docuList.forEach((item) => {
          item.children = [];
          item.instance = item.instance || {
            is_used: true,
          };
          if (item.is_required && item.instance.is_used && !item.instance.url) {
            ++count;
          }
          docuList.forEach((subItem) => {
            if (subItem.parent && subItem.parent === item.id) {
              item.children.push(subItem);
              childrenList.push(subItem);
            }
          });
        });
        const templateList = docuList.filter(item => !childrenList.map(_ => _.id).includes(item.id));
        this.notCompletedCount = count;
        this.tableList = JSON.parse(JSON.stringify(templateList));
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      } finally {
        this.isLoading = false;
      }
    },

    handleEdit(payload) {
      this.$set(payload, 'isEdit', true);
      this.$set(payload, 'isUseBackup', payload.instance.is_used);
      this.$set(payload, 'urlBackup', payload.instance.url || '');
    },

    handleSave(payload) {
      this.$delete(payload, 'isEdit');
      const flag = !payload.instance.url;
      if (flag) {
        this.updateDocumentInstance(payload);
      } else {
        this.updateDocumentInstanceByExist(payload);
      }
    },

    async updateDocumentInstance(payload) {
      const params = {
        url: payload.urlBackup,
        is_used: payload.isUseBackup,
        doc_template: payload.id,
        appCode: this.curAppCode,
      };
      try {
        const res = await this.$store.dispatch('docuManagement/updateDocumentInstance', params);
        payload.instance = Object.assign(payload.instance, { ...res });
        this.$delete(payload, 'isUseBackup');
        this.$delete(payload, 'urlBackup');
        if (payload.is_required && payload.instance.is_used && !payload.instance.url) {
          // eslint-disable-next-line no-plusplus
          ++this.notCompletedCount;
        }
        if (!(payload.is_required && payload.instance.is_used && !payload.instance.url) && this.notCompletedCount) {
          // eslint-disable-next-line no-plusplus
          --this.notCompletedCount;
        }
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      }
    },

    async updateDocumentInstanceByExist(payload) {
      const params = {
        url: payload.urlBackup,
        is_used: payload.isUseBackup,
        id: payload.instance.id,
        appCode: this.curAppCode,
      };
      try {
        const res = await this.$store.dispatch('docuManagement/updateDocumentInstanceByExist', params);
        payload.instance.is_used = res.is_used;
        payload.instance.url = res.url;
        payload.instance.latest_operator = res.latest_operator;
        payload.instance.updated = res.updated;
        this.$delete(payload, 'isUseBackup');
        this.$delete(payload, 'urlBackup');
        if (payload.is_required && payload.instance.is_used && !payload.instance.url) {
          ++this.notCompletedCount;
        }
        if (!(payload.is_required && payload.instance.is_used && !payload.instance.url) && this.notCompletedCount) {
          --this.notCompletedCount;
        }
      } catch (res) {
        this.$paasMessage({
          limit: 1,
          theme: 'error',
          message: res.message,
        });
      }
    },

    handleCopy(payload) {
      const el = document.createElement('textarea');
      el.value = payload.instance.url;
      el.setAttribute('readonly', '');
      el.style.position = 'absolute';
      el.style.left = '-9999px';
      document.body.appendChild(el);
      const selected = document.getSelection().rangeCount > 0 ? document.getSelection().getRangeAt(0) : false;
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      if (selected) {
        document.getSelection().removeAllRanges();
        document.getSelection().addRange(selected);
      }
      this.$bkMessage({ theme: 'primary', message: this.$t('复制成功'), delay: 2000, dismissable: false });
    },

    handleUrlInput(value, $event, payload) {
      this.$set(payload, 'urlBackup', value);
    },

    handleCancel(payload) {
      this.$delete(payload, 'isEdit');
    },

    handleSwitchChange(value, payload) {
      this.$set(payload, 'isUseBackup', value);
    },
  },
};
</script>
<style lang="scss">
    @import '~@/assets/css/mixins/ellipsis.scss';
    .docu-container{
      background: #fff;
      margin-top: 16px;
      padding: 16px 24px;
    }
    .paas-docu-manager-wrapper {
        .link {
            font-size: 12px;
            &:hover {
                color: #699df4;
            }
        }
        .middle {
            position: relative;
        }
        .empty-wrapper {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            i {
                font-size: 65px;
                color: #c3cdd7;
            }
            .empty-text {
                font-size: 12px;
                text-align: center;
            }
        }
        .docu-manager-custom-table {
            margin-top: 16px;
            border: none;
            thead {
                border-top: 1px solid #dcdee5;
                border-bottom: 1px solid #dcdee5;
                th {
                    padding-left: 30px;
                    color: #313238;
                    font-weight: 400 !important;
                }
                th:nth-child(1) {
                    border-right: 1px solid #dcdee5;
                }
            }
            tbody {
                tr {
                    td {
                        padding-left: 30px;
                    }
                    .url-td {
                        .bk-form-control {
                            margin: 5px 0;
                        }
                    }
                    td:nth-child(1) {
                        border-right: 1px solid #dcdee5;
                    }
                    .children-td {
                        padding: 0;
                        border-bottom: 1px solid #dcdee5;
                    }
                }
                .active {
                    color: #62d18a;
                }
                .name {
                    display: inline-block;
                    max-width: 145px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    vertical-align: bottom;
                }
                .is-required {
                    color: #ea3636;
                }
            }
            .sub-table {
                position: relative;
                top: 1px;
                border: none;
                table-layout: fixed;
                tr {
                    td:nth-child(1) {
                        border-right: none !important;
                    }
                    .url-td {
                        .bk-form-control {
                            margin: 5px 0;
                        }
                    }
                }
                tr:last-child {
                    td {
                        border-bottom: 1px solid #dcdee5 !important;
                    }
                }
                .name {
                    display: inline-block;
                    max-width: 145px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    white-space: nowrap;
                    vertical-align: bottom;
                }
            }
        }
    }
</style>
