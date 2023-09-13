<template>
  <div class="code-inspection">
    <section class="card-item quality-star">
      <div class="quality-left">
        <div class="star">
          <span class="title">{{$t('质量星级')}}</span>
          <bk-rate :rate="showRate" :edit="false"></bk-rate>
          <span class="score">{{codeDetails.rdIndicatorsScore ?? '--'}} {{$t('分')}}</span>
        </div>
        <p class="mt5 desc">{{$t('每次部署应用时，异步执行代码检查')}}</p>
      </div>
      <div class="quality-right">
        <p>
          {{$t('最近检查时间：')}}{{codeDetails.lastAnalysisTime || '--'}}
          <i class="paasng-icon paasng-process-file ml5"
            v-if="codeDetails.detailUrl"
            @click="handleToDetail(codeDetails.detailUrl)"
          />
        </p>
      </div>
    </section>
    <section class="card-item">
      <div class="overview-item">
        <h3>{{codeDetails.codeSecurityScore ?? '--'}}</h3>
        <div class="desc">
          <i class="paasng-icon paasng-anquan mr5" />
          <span>{{$t('代码安全')}}</span>
        </div>
      </div>
      <div class="overview-item">
        <h3>{{codeDetails.codeStyleScore ?? '--'}}</h3>
        <div class="desc">
          <i class="paasng-icon paasng-guifan mr5" />
          <span>{{$t('代码规范')}}</span>
        </div>
      </div>
      <div class="overview-item">
        <h3>{{codeDetails.codeMeasureScore ?? '--'}}</h3>
        <div class="desc">
          <i class="paasng-icon paasng-duliang mr5" />
          <span>{{$t('代码度量')}}</span>
        </div>
      </div>
    </section>
    <section class="card-item check-details">
      <h4>{{$t('代码检查详情')}}</h4>
      <ul class="detail-wrapper" v-if="codeDetails.lastAnalysisResultList?.length">
        <li
          v-for="(item, index) in codeDetails.lastAnalysisResultList"
          :key="index"
          class="item"
          @click="handleToDetail(item.defectUrl)">
          <p>{{item.displayName}}</p>
          <div class="container">
            <span class="number">{{item.defectCount}}</span>
            <span class="fix">{{$t('个')}}</span>
          </div>
        </li>
      </ul>
      <div class="empty-wrapper" v-else>
        <bk-exception
          class="exception-wrap-item exception-part"
          type="empty"
          scene="part"
        >
        </bk-exception>
      </div>
    </section>
  </div>
</template>

<script>
export default {
  props: {
    codeDetails: {
      type: Object,
      default: () => {}
    }
  },

  computed: {
    showRate() {
      if (this.codeDetails.rdIndicatorsScore) {
        return this.codeDetails.rdIndicatorsScore / 100 * 5;
      }
      return 0;
    },
  },

  methods: {
    handleToDetail(url) {
      window.open(url, '_blank');
    },
  },
};
</script>

<style lang="scss" scoped>
@media (max-width: 1250px) {
  .check-details .detail-wrapper .item {
    margin-right: 8px !important;
  }
}
  
.code-inspection {
  .card-item {
    display: flex;
    padding: 24px;
    background-color: #fff;
    box-shadow: 0 2px 4px 0 #1919290d;
    border-radius: 2px;
    margin-bottom: 16px;

    .overview-item {
      flex: 1;
      text-align: center;
      border-right: 2px solid #eaebf0;

      &:last-child {
        border-right: none;
      }

      h3 {
        font-size: 30px;
        color: #313238;
        font-weight: 400;
      }
      .desc {
        margin-top: 8px;
        i {
          color: #3a84ff;
        }
        span {
          font-size: 14px;
          color: #00000099;
        }
      }
    }
  }

  .empty-wrapper {
    margin: 24px 0;
  }

  .quality-star {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .quality-right {
      i {
        cursor: pointer;
        color: #3a84ff;
      }
    }

    .star {
      display: flex;
      align-items: center;
      .title {
        font-weight: 700;
        font-size: 20px;
        color: #313238;
        margin-right: 24px;
      }
      .score {
        margin-left: 15px;
        color: #313238;
      }
    }
    .desc {
      font-size: 14px;
      color: #979ba5;
    }
  }

  .check-details {
    display: block;
    h4 {
      color: #313238;
    }

    .detail-wrapper {
      display: flex;
      flex-wrap: wrap;
      justify-content: flex-start;
    }

    .item {
      width: 283px;
      height: 106px;
      padding: 12px 16px;
      background: #f5f7fa;
      border-radius: 2px;
      margin-right: 8px;
      margin-bottom: 8px;
      cursor: pointer;

      &:nth-child(3n) {
        margin-right: 0;
      }

      .container {
        width: 100%;
        height: 100%;
        display: flex;
        justify-content: center;
        align-items: center;
        .number {
          font-size: 30px;
          color: #313238;
        }
        .fix {
          transform: translateY(3px);
          margin-left: 5px;
        }
      }
    }
  }
}
</style>
