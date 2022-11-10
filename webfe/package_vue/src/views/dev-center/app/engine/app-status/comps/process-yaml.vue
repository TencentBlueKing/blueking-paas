<template>
    <div>
        <paas-content-loader :is-loading="screenIsLoading" placeholder="deploy-yaml-loading" :offset-top="20" :offset-left="20" class="deploy-action-box">
            <div class="process-yaml-container">
                <resource-editor
                    v-model="detail"
                    :height="fullScreen ? clientHeight : height"
                    ref="editorRef"
                    key="editor"
                    v-bkloading="{ isLoading, opacity: 1, color: '#1a1a1a' }"
                    @error="handleEditorErr">
                </resource-editor>
                <EditorStatus class="status-wrapper" :message="editorErr.message" v-show="!!editorErr.message"></EditorStatus>
            </div>
        </paas-content-loader>
        <!-- <bk-button theme="primary"
            class="mt20"
            :loading="deployLoading"
            @click="handleDeploy">
            保存并发布
        </bk-button> -->
    </div>
</template>
<script>
    import appBaseMixin from '@/mixins/app-base-mixin.js';
    import ResourceEditor from './deploy-resource-editor';
    import EditorStatus from './deploy-resource-editor/editor-status';
    // import _ from 'lodash';
    export default {
        components: {
            ResourceEditor,
            EditorStatus
        },
        mixins: [appBaseMixin],
        props: {
            env: {
                type: String,
                default: ''
            },
            deployId: {
                type: Number,
                default: 0
            }
        },
        data () {
            return {
                fullScreen: false,
                clientHeight: document.body.clientHeight,
                height: 600,
                isLoading: false,
                editorErr: {
                    type: '',
                    message: ''
                },
                detail: {},
                deployLoading: false,
                screenIsLoading: true,
                isFetch: false
            };
        },
        computed: {
        },
        watch: {
            deployId: {
                handler (val) {
                    if (val) {
                        this.init();
                    }
                },
                immediate: true
            }
        },
        mounted () {
            this.init();
        },
        methods: {
            async init () {
                if (this.isFetch) return;
                try {
                    this.isFetch = true;
                    const res = await this.$store.dispatch('deploy/getCloudAppDeployYaml', {
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        env: this.env,
                        deployId: this.deployId
                    });
                    this.$nextTick(() => {
                        this.detail = res.manifest;
                        this.$refs.editorRef.setValue(this.detail);
                    });
                } catch (e) {
                    if (e.code !== 'GET_DEPLOYMENT_FAILED') {
                        this.$paasMessage({
                            theme: 'error',
                            message: e.detail || e.message || this.$t('接口异常')
                        });
                    }
                } finally {
                    this.isFetch = false;
                    this.screenIsLoading = false;
                }
            },
            async handleDeploy () {
                try {
                    this.deployLoading = true;
                    await this.$store.dispatch('deploy/sumbitCloudApp', {
                        params: { manifest: this.detail },
                        appCode: this.appCode,
                        moduleId: this.curModuleId,
                        env: this.env
                    });
                    this.$paasMessage({
                        theme: 'success',
                        message: '操作成功'
                    });
                    this.$emit('getCloudAppInfo');
                } catch (e) {
                    this.$paasMessage({
                        theme: 'error',
                        message: e.detail || e.message
                    });
                } finally {
                    this.deployLoading = false;
                }
            },
            handleEditorErr (err) { // 捕获编辑器错误提示
                this.editorErr.type = 'content'; // 编辑内容错误
                this.editorErr.message = err;
            }
        }
    };
</script>
<style scope>
.process-yaml-container{
    position: relative;
    padding: 0 20px 20px 20px;
}
</style>
