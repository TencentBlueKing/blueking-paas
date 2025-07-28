<template>
  <div class="paas-deploy-log-deploy-stage-wrapper">
    <label class="title">
      {{ $t('部署阶段') }}
      <status-item
        v-if="abnormalCount > 0"
        status="abnormal"
        :abnormal-count="abnormalCount"
      />
    </label>

    <section class="content-wrapper" v-if="releaseList.length">
      <section
        ref="content"
        class="log-content"
      >
        <pre
          v-for="(item, index) in releaseList"
          :key="index"
          class="log-item"
          v-dompurify-html="item"
        />
      </section>
    </section>

    <section
      v-bkloading="{ isLoading: loading, color: '#2a2b2f' }"
      class="content"
    >
      <div class="process-content">
        <template v-if="curProcessList.length > 0">
          <process-item
            v-for="item in curProcessList"
            :key="`${item.name}${item.instanceData.display_name}`"
            :status="item.state"
            :title="item.name"
            :instance-name="item.instanceData.name"
            :expanded="item.expanded"
            :sub-title="item.instanceData.display_name"
          />
        </template>
        <template v-else>
          <div class="empty-process">
            {{ $t('无执行中的进程') }}
          </div>
        </template>
      </div>
    </section>
  </div>
</template>
<script>
import appBaseMixin from '@/mixins/app-base-mixin.js';
import ProcessItem from './render-process-item';
import StatusItem from './render-status-item';
export default {
  name: '',
  components: {
    ProcessItem,
    StatusItem,
  },
  mixins: [appBaseMixin],
  props: {
    title: {
      type: String,
      default: '',
    },
    releaseList: {
      type: Array,
      default: () => [],
    },
    data: {
      type: Array,
      default: () => [],
    },
    loading: {
      type: Boolean,
      default: false,
    },
    environment: {
      type: String,
      default: 'stag',
    },
  },
  data() {
    return {
      curProcessList: [],
    };
  },
  computed: {
    abnormalCount() {
      let abnormalLen = 0;
      this.data.forEach((item) => {
        item.instances.forEach((instanceItem) => {
          if (!['Starting', 'Pending', 'Running'].includes(instanceItem.state)) {
            // eslint-disable-next-line no-plusplus
            ++abnormalLen;
          }
        });
      });
      return abnormalLen;
    },
  },
  watch: {
    data: {
      handler(value) {
        this.curProcessList = this.handleProcessData(value);
      },
      immediate: true,
      deep: true,
    },
  },
  methods: {
    handleProcessData(payload) {
      if (!payload || payload.length < 1) {
        return [];
      }
      const processList = [];
      payload.forEach((item) => {
        item.instances.forEach((instanceItem) => {
          processList.push({
            ...item,
            state: instanceItem.state,
            instanceData: { ...instanceItem },
          });
        });
      });
      return processList;
    },
  },
};
</script>
<style lang="scss">
    .paas-deploy-log-deploy-stage-wrapper {
        .title {
            display: inline-block;
            margin-bottom: 8px;
            font-size: 14px;
            color: #979ba5;
        }
        .content-wrapper {
            position: relative;
            width: 100%;
            min-height: 60px;
            background: #2a2b2f;
            border-radius: 2px;
            .screen-wrapper {
                position: absolute;
                top: 15px;
                right: 20px;
                cursor: pointer;
                i {
                    font-size: 16px;
                    color: #63656e;
                }
            }
        }
        .log-content {
            padding: 15px 20px;
            width: 100%;
            max-height: 500px;
            overflow-y: auto;
            &::-webkit-scrollbar {
                width: 4px;
                background-color: lighten(transparent, 80%);
            }
            &::-webkit-scrollbar-thumb {
                height: 5px;
                border-radius: 2px;
                background-color: #63656e;
            }
            .log-item {
                line-height: 20px;
                font-size: 12px;
                color: #c4c6cc;
                font-family: Consolas,source code pro,Bitstream Vera Sans Mono,Courier,monospace,\\5FAE\8F6F\96C5\9ED1,Arial;
            }
        }
        .content {
            width: 100%;
            background: #2a2b2f;
            border-radius: 2px;
            &::-webkit-scrollbar {
                width: 4px;
                background-color: lighten(transparent, 80%);
            }
            &::-webkit-scrollbar-thumb {
                height: 5px;
                border-radius: 2px;
                background-color: #63656e;
            }
            .log-item {
                display: flex;
                justify-content: flex-start;
                line-height: 20px;
                font-size: 12px;
                color: #fff;
            }
        }
        .process-content {
            position: relative;
            min-height: 90px;
            padding: 10px 20px 20px 20px;
            .log-empty,
            .empty-process {
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                font-size: 12px;
                color: #979ba5;
            }
        }
    }
</style>
