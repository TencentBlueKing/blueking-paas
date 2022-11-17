<template>
  <div :class="['bk-spin-loading', `bk-spin-loading-${size}`, `bk-spin-loading-${theme}`, extCls]">
    <div class="rotate rotate1" />
    <div class="rotate rotate2" />
    <div class="rotate rotate3" />
    <div class="rotate rotate4" />
    <div class="rotate rotate5" />
    <div class="rotate rotate6" />
    <div class="rotate rotate7" />
    <div class="rotate rotate8" />
  </div>
</template>
<script>
    export default {
        name: 'RoundLoading',
        props: {
            size: {
                type: String,
                default: 'mini',
                validator: function (value) {
                    return ['large', 'small', 'mini'].includes(value);
                }
            },
            theme: {
                type: String,
                default: 'primary',
                validator: function (value) {
                    return ['primary', 'danger', 'success', 'white', 'warning'].includes(value);
                }
            },
            extCls: {
                type: String,
                default: ''
            }
        }
    };
</script>
<style lang="scss">
    .bk-spin-loading,
    .bk-loading2 {
        width: 39px;
        height: 39px;
        position: relative;
        margin: auto;
        display: inline-block;
        vertical-align: middle;
    }

    .bk-spin-loading .rotate,
    .bk-loading2 .rotate {
        position: absolute;
        top: 77%;
        right: 43%;
        background-color: none;
        background-color: #39424e\9\0;
        width: 6px;
        height: 8px;
        transform-origin: 50% -10px;
        border-radius: 8px;
        transform: scale(0.4);
        animation-name: fade;
        animation-duration: 1.2s;
        animation-iteration-count: infinite;
        animation-direction: normal;
    }

    .bk-spin-loading.bk-spin-loading-success .rotate,
    .bk-loading2.bk-spin-loading-success .rotate {
        background: #30d878\9\0;
        animation-name: fadeSuccess;
    }

    .bk-spin-loading.bk-spin-loading-danger .rotate,
    .bk-loading2.bk-spin-loading-danger .rotate {
        background: #ff5656\9\0;
        animation-name: fadeDanger;
    }

    .bk-spin-loading.bk-spin-loading-warning .rotate,
    .bk-loading2.bk-spin-loading-warning .rotate {
        background: #ffb400\9\0;
        animation-name: fadeWarning;
    }

    .bk-spin-loading.bk-spin-loading-primary .rotate,
    .bk-loading2.bk-spin-loading-primary .rotate {
        background: #3c96ff\9\0;
        animation-name: fadePrimary;
    }

    .bk-spin-loading.bk-spin-loading-white .rotate,
    .bk-loading2.bk-spin-loading-white .rotate {
        background: #fff\9\0;
        animation-name: fadeWhite;
    }

    .bk-spin-loading .rotate1,
    .bk-loading2 .rotate1 {
        animation-delay: 0.45s;
        transform: rotate(-90deg);
    }

    .bk-spin-loading .rotate2,
    .bk-loading2 .rotate2 {
        animation-delay: 0.6s;
        transform: rotate(-45deg);
    }

    .bk-spin-loading .rotate3,
    .bk-loading2 .rotate3 {
        animation-delay: 0.75s;
        transform: rotate(0deg);
    }

    .bk-spin-loading .rotate4,
    .bk-loading2 .rotate4 {
        animation-delay: 0.9s;
        transform: rotate(45deg);
    }

    .bk-spin-loading .rotate5,
    .bk-loading2 .rotate5 {
        animation-delay: 1.05s;
        transform: rotate(90deg);
    }

    .bk-spin-loading .rotate6,
    .bk-loading2 .rotate6 {
        animation-delay: 1.2s;
        transform: rotate(135deg);
    }

    .bk-spin-loading .rotate7,
    .bk-loading2 .rotate7 {
        animation-delay: 1.35s;
        transform: rotate(180deg);
    }

    .bk-spin-loading .rotate8,
    .bk-loading2 .rotate8 {
        animation-delay: 1.5s;
        transform: rotate(-135deg);
    }

    .bk-spin-loading.bk-spin-loading-large,
    .bk-loading2.bk-spin-loading-large {
        width: 69px;
        height: 69px;
    }

    .bk-spin-loading.bk-spin-loading-large .rotate,
    .bk-loading2.bk-spin-loading-large .rotate {
        width: 10px;
        height: 14px;
        transform-origin: 50% -18px;
    }

    .bk-spin-loading.bk-spin-loading-small,
    .bk-loading2.bk-spin-loading-small {
        width: 27px;
        height: 27px;
    }

    .bk-spin-loading.bk-spin-loading-small .rotate,
    .bk-loading2.bk-spin-loading-small .rotate {
        width: 4px;
        height: 5px;
        transform-origin: 50% -7px;
    }

    .bk-spin-loading.bk-spin-loading-mini,
    .bk-loading2.bk-spin-loading-mini {
        width: 16px;
        height: 16px;
    }

    .bk-spin-loading.bk-spin-loading-mini .rotate,
    .bk-loading2.bk-spin-loading-mini .rotate {
        width: 2px;
        height: 3px;
        transform-origin: 50% -4px;
    }

    @keyframes fade {
        0% {
            background-color: #39424e;
        }

        100% {
            background-color: none;
        }
    }

    @keyframes fadeSuccess {
        0% {
            background-color: #30d878;
        }

        100% {
            background-color: none;
        }
    }

    @keyframes fadePrimary {
        0% {
            background-color: #3c96ff;
        }

        100% {
            background-color: none;
        }
    }

    @keyframes fadeDanger {
        0% {
            background-color: #ff5656;
        }

        100% {
            background-color: none;
        }
    }

    @keyframes fadeWarning {
        0% {
            background-color: #ffb400;
        }

        100% {
            background-color: none;
        }
    }

    @keyframes fadeWhite {
        0% {
            background-color: white;
        }

        100% {
            background-color: none;
        }
    }

    .bk-loading .bk-loading1,
    .bk-loading1 {
        position: relative;
        width: 44px;
        height: 14px;
        margin: auto;
        .point {
            position: absolute;
            top: 0;
            width: 14px;
            height: 14px;
            animation-name: animate;
            animation-duration: .8s;
            animation-iteration-count: infinite;
            animation-direction: normal;
            transform: scale(.3);
            border-radius: 50%;
            background-color: #666;
        }
        .point1 {
            left: 0;
            animation-delay: 0.1s;
        }
        .point2 {
            left: 10px;
            animation-delay: 0.25s;
        }
        .point3 {
            left: 20px;
            animation-delay: 0.4s;
        }
        .point4 {
            left: 30px;
            animation-delay: 0.55s;
        }
    }

    @keyframes animate {
        0% {
            transform: scale(.5)
        }

        100% {
            transform: scale(.3)
        }
    }
</style>
