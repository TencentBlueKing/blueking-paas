const tableList = (app) => {
  app.get('/api/table', (req, res) => {
    res.json({
      code: 0,
      message: '',
      data: {
        list: [
          {
            id: 1,
            ip: '127.0.0.1',
            source: '微信',
            status: '正常',
            create_time: '2018-05-25 15:02:24',
            children: [],
          },
        ],
      },
    });
  });
};

module.exports = tableList;
