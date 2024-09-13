<template>
  <div class="base-info-container card-style">
    <p class="title">{{ $t('基本信息-title') }}</p>
    <p class="description">{{ $t('管理员、开发者可以修改插件名称等基本信息') }}</p>
    <section class="main">
      <ul class="detail-wrapper">
        <li class="item-info">
          <div class="describe">
            {{ $t('应用 logo') }}
          </div>
          <div class="content">
            <div class="logo-uploader item-logn-content">
              <div class="preview">
                <img :src="curPluginInfo.logo || '/static/images/default_logo.png'" />
              </div>
              <div
                v-if="isChangePluginLogo"
                class="preview-btn pl20"
              >
                <div>
                  <bk-button
                    :theme="'default'"
                    class="upload-btn mt5"
                  >
                    {{ $t('更换图片') }}
                    <input
                      type="file"
                      accept="image/jpeg, image/png"
                      value=""
                      name="logo"
                      @change="handlerUploadFile"
                    />
                  </bk-button>
                  <p
                    class="tip"
                    style="line-height: 1"
                  >
                    {{ $t('支持jpg、png等图片格式，图片尺寸为72*72px，不大于2MB。') }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </li>
        <li class="item-info">
          <div class="describe">
            {{ $t('插件 ID') }}
          </div>
          <div class="content">{{ pluginInfo.id || '--' }}</div>
        </li>
        <li class="item-info">
          <div class="describe">
            {{ $t('插件名称') }}
          </div>
          <div :class="['content', { 'no-padding-lf': isEdit }]">
            <bk-form ext-cls="name-form-cls" form-type="inline">
              <bk-form-item label="" ext-cls="plugin-name-item-cls">
                <template v-if="isEdit">
                  <bk-input
                    ref="pluginNameRef"
                    v-model="pluginName"
                    :placeholder="$t('请输入插件名称')"
                    :clearable="false"
                    :maxlength="20"
                    :readonly="isLoading"
                    @enter="updatePluginBaseInfo"
                    @blur="updatePluginBaseInfo"
                  />
                  <round-loading v-if="isLoading" class="loading" />
                </template>
                <div
                  v-else
                  class="plugin-name-box"
                >
                  <span>{{ pluginInfo.name_zh_cn || '--' }}</span>
                  <i
                    v-bk-tooltips="$t('编辑')"
                    class="paasng-icon paasng-edit-2 plugin-name-icon"
                    @click="showEdit"
                  />
                </div>
              </bk-form-item>
            </bk-form>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>

<script>
import pluginBaseMixin from '@/mixins/plugin-base-mixin';
export default {
  mixins: [pluginBaseMixin],
  props: {
    pluginInfo: {
      type: Object,
      default: () => {},
    },
  },
  data() {
    return {
      pluginName: '',
      isEdit: false,
      isLoading: false,
    };
  },
  computed: {
    // 是否可以更换插件logo
    isChangePluginLogo() {
      return this.curPluginInfo.role && [2].indexOf(this.curPluginInfo.role.id) !== -1;
    },
  },
  watch: {
    pluginInfo(newValue) {
      this.init(newValue);
    },
  },
  created() {
    this.init(this.pluginInfo);
  },
  methods: {
    init(info) {
      this.pluginName = info.name_zh_cn;
    },
    /**
     * 选择文件后回调处理
     * @param {Object} e 事件
     */
    async handlerUploadFile(e) {
      e.preventDefault();
      const { files } = e.target;
      const data = new FormData();
      const fileInfo = files[0];
      const maxSize = 2 * 1024;
      // 支持jpg、png等图片格式，图片尺寸为72*72px，不大于2MB。验证
      const imgSize = fileInfo.size / 1024;

      if (imgSize > maxSize) {
        this.$paasMessage({
          theme: 'error',
          message: this.$t('文件大小应<2M！'),
        });
        return;
      }

      data.append('logo', files[0]);
      const params = {
        pdId: this.pdId,
        pluginId: this.pluginId,
        data,
      };

      try {
        await this.$store.dispatch('plugin/uploadPluginLogo', params);
        this.$emit('updata-log');
        this.$paasMessage({
          theme: 'success',
          message: this.$t('logo上传成功！'),
        });
      } catch (e) {
        this.$paasMessage({
          theme: 'error',
          message: e.message,
        });
      }
    },
    // 更新基本信息
    async updatePluginBaseInfo() {
      if (this.pluginName === this.pluginInfo.name_zh_cn) {
        this.closeEditing();
        return;
      }
      try {
        // isloading 开启loading
        this.isLoading = true;
        await this.$store.dispatch('plugin/updatePluginBaseInfo', {
          pdId: this.pdId,
          pluginId: this.pluginId,
          data: {
            name: this.pluginName,
          },
        });
        this.$bkMessage({
          theme: 'success',
          message: this.$t('基本信息修改成功！'),
        });
        // 通知父组件更新
        this.$emit('get-base-info');
      } catch (e) {
        this.$bkMessage({
          theme: 'error',
          message: e.detail || e.message || this.$t('接口异常'),
        });
      } finally {
        this.closeEditing();
        this.isLoading = false;
      }
    },
    closeEditing() {
      this.isEdit = false;
      this.pluginName = this.pluginInfo.name_zh_cn;
    },
    showEdit() {
      this.isEdit = true;
      this.$nextTick(() => {
        this.$refs.pluginNameRef.focus();
      });
    },
  },
};
</script>

<style lang="scss" scoped>
.base-info-container {
  padding: 24px;
  .title {
    font-weight: 700;
    font-size: 14px;
    color: #313238;
    line-height: 22px;
  }
  .description {
    margin-top: 4px;
    margin-bottom: 8px;
    font-size: 12px;
    color: #979ba5;
    line-height: 20px;
  }
  .plugin-name-item-cls {
    position: relative;
    .loading {
      position: absolute;
      right: 16px;
      top: 50%;
      transform: translateY(-50%);
    }
  }
  .detail-wrapper {
    border: 1px solid #DCDEE5;
    .item-info {
      display: flex;
      min-height: 42px;
      border-top: 1px solid #DCDEE5;

      &:first-child {
        border-top: none;
      }
      .describe,
      .content {
        display: flex;
        align-items: center;
      }
      .describe {
        flex-shrink: 0;
        justify-content: center;
        width: 180px;
        text-align: right;
        font-size: 12px;
        color: #313238;
        line-height: normal;
        background: #fafbfd;
      }
      .content {
        flex-wrap: wrap;
        line-height: 1.5;
        word-break: break-all;
        flex: 1;
        font-size: 12px;
        color: #63656E;
        padding-left: 16px;
        border-left: 1px solid #DCDEE5;

        &.no-padding-lf {
            padding-left: 0;
        }

        :deep(.name-form-cls) {
            width: 100%;
            .bk-form-item,
            .bk-form-content {
                width: 100%;
                input {
                    border-radius: 0 2px 2px 0;
                    height: 42px;
                }
            }
        }

        .plugin-name-icon {
          margin-left: 5px;
          cursor: pointer;
          color: #3a84ff;
          font-size: 16px;
        }

        .logo-uploader {
          display: flex;
          overflow: hidden;
          padding: 20px;

          .preview {
            img {
              width: 64px;
              height: 64px;
              border-radius: 2px;
            }
          }

          .upload-btn {
            width: 100px;
            overflow: hidden;
            margin-bottom: 10px;
            input {
              position: absolute;
              left: 0;
              top: 0;
              z-index: 10;
              height: 100%;
              min-height: 40px;
              width: 100%;
              opacity: 0;
              cursor: pointer;
            }
          }
        }
      }
    }
  }
}
</style>
