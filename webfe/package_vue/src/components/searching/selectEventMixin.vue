<script>
/*
    必须实现 getSelectListLength 方法
*/
    export default {
        data: function () {
            return {
                curActiveIndex: -1
            };
        },
        methods: {
            // 处理键盘事件方法
            onKeyUp: function () {
                if (this.getSelectListLength() === 0 || this.curActiveIndex === 0) {
                    this.curActiveIndex = -1;
                    return this.$emit('key-up-overflow');
                }
                if (this.curActiveIndex === -1) {
                    // 未被选中, 说明父组件从下面选起
                    this.curActiveIndex = this.getSelectListLength() - 1;
                } else {
                    this.curActiveIndex--;
                }
            },
            onKeyDown: function () {
                if (this.getSelectListLength() === 0 || this.curActiveIndex === this.getSelectListLength() - 1) {
                    this.curActiveIndex = -1;
                    return this.$emit('key-down-overflow');
                }
                this.curActiveIndex = (this.curActiveIndex + 1) % this.getSelectListLength();
            },
            getSelectListLength: function () {
                console.error('this method must be override');
            }
        }
    };
</script>
