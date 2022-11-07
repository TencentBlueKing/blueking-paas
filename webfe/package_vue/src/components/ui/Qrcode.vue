<template>
    <canvas></canvas>
</template>
<script>
    import QRious from 'qrious';

    export default {
        props: {
            url: {
                type: String,
                default: ''
            },
            size: {
                type: Number,
                default: 200
            }
        },
        data () {
            return {
                instance: undefined
            };
        },
        mounted: function () {
            this.instance = new QRious({
                element: this.$el,
                value: this.url,
                size: this.size
            });
        }
    };
</script>
