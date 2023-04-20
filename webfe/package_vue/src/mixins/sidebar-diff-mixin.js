export default {
  data () {
    return {
      // 初始化状态
      initDataStr: ''
    };
  },
  methods: {
    /**
     * 侧边栏离开，二次确认
     * @return true / error
     */
    $isSidebarClosed (targetDataStr) {
      const isEqual = this.initDataStr === targetDataStr;
      return new Promise((resolve, reject) => {
        // 未编辑
        if (isEqual) {
          resolve(true);
        } else {
          // 已编辑
          this.$bkInfo({
            extCls: 'sideslider-close-cls',
            title: this.$t('确认离开当前页？'),
            subTitle: this.$t('离开将会导致未保存信息丢失'),
            okText: this.$t('离开'),
            confirmFn () {
              resolve(true);
            },
            cancelFn () {
              resolve(false);
            }
          });
        }
      });
    },
    initSidebarFormData (data) {
      this.initDataStr = JSON.stringify(data);
    }
  }
};
