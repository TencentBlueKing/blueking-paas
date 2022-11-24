from paas_wl.utils.basic import HumanizeURL


class TestHumanizeURL:
    def test_default_port(self):
        url = HumanizeURL('http', 'example.com', 80, '/')
        assert url.to_str() == 'http://example.com/'

    def test_customized_port(self):
        url = HumanizeURL('http', 'example.com', 8080, '/', 'foo=1')
        assert url.to_str() == 'http://example.com:8080/?foo=1'
