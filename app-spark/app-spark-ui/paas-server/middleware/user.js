// 获取 OA 登录用户详情
module.exports = async function user(req, res, next) {
  if (req.path !== '/api/user' && req.path !== '/user') {
    next();
    return;
  }

  const loginBase = (process.env.BK_LOGIN_URL || '').replace(/\/$/, '');
  if (!loginBase) {
    res.status(401);
    res.json({
      code: 401,
      message: '未配置 BK_LOGIN_URL',
    });
    return;
  }

  const request = require('request');
  request(`${loginBase}/user/get_info?bk_ticket=${req.cookies.bk_ticket}`, (err, response, body) => {
    if (err) {
      return;
    }

    const data = JSON.parse(body || '{}');

    // 有登录状态
    if (data.ret === 0) {
      const {
        username,
        avatar_url,
      } = data.data;
      res.json({
        code: 0,
        message: data.msg,
        data: {
          username,
          avatar_url,
        },
      });
      return;
    }
    // 登录状态失效
    res.status(401);
    res.json({
      code: 401,
      message: data.msg,
    });
  });
};
