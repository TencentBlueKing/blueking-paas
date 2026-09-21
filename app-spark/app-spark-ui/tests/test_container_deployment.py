"""Exercise the real entrypoint and Nginx in the production base image.

Run with: python3 -m unittest discover -s tests -v
Requires Docker and the image selected by CONTAINER_TEST_IMAGE (nginx:1.30-alpine
by default). No npm installation or application image build is required.
"""

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get("CONTAINER_TEST_IMAGE", "nginx:1.30-alpine")
ENTRYPOINT = "/test/docker-entrypoint.sh"


class ContainerDeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.html = self.root / "html"
        (self.html / "static").mkdir(parents=True)
        (self.html / "index.html").write_text(
            '<html><script src="__APP_SPARK_RT_BK_SITE_URL__/static/app.js"></script></html>',
            encoding="utf-8",
        )
        (self.html / "static/app.js").write_text(
            "const config = {site: '__APP_SPARK_RT_BK_SITE_URL__', "
            "login: '__APP_SPARK_RT_BK_LOGIN_URL__', "
            "template: '__APP_SPARK_RT_BK_TEMPLATE_URL__'};",
            encoding="utf-8",
        )
        (self.html / "static/app.js.map").write_text("private source map")
        (self.html / ".secret").write_text("private dotfile")
        (self.html / "static/.secret").write_text("private dotfile")
        (self.html / "robots.txt").write_text("User-agent: *")

    def run_container(self, env=None, command=None, env_file=None, raw=False):
        args = ["docker", "run", "--rm", "--entrypoint", "sh"]
        mounts = {
            self.html: "/opt/app-spark/html",
            PROJECT_ROOT / "docker/docker-entrypoint.sh": ENTRYPOINT,
            PROJECT_ROOT / "docker/nginx-default.conf.template": ("/opt/app-spark/nginx-default.conf.template"),
            PROJECT_ROOT / "docker/security_headers.conf": ("/etc/nginx/security_headers.conf"),
        }
        if env_file is not None:
            path = self.root / "runtime.env"
            path.write_text(env_file, encoding="utf-8")
            mounts[path] = "/env/.env"
        for source, destination in mounts.items():
            args.extend(["-v", f"{source}:{destination}:ro"])
        for key, value in (env or {}).items():
            args.extend(["-e", f"{key}={value}"])
        args.append(IMAGE)
        if not raw:
            args.extend([ENTRYPOINT, "sh"])
        args.extend(
            [
                "-c",
                command
                or "cat /usr/share/nginx/html/index.html "
                "/usr/share/nginx/html/static/app.js "
                "/etc/nginx/conf.d/default.conf",
            ]
        )
        return subprocess.run(args, capture_output=True, text=True, timeout=45, check=False)

    def assert_success(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def request_paths(self, site, paths, conditional=False):
        # A future modification date exposes stale 304 responses after runtime injection.
        extra_header = "If-Modified-Since: Thu, 31 Dec 2037 23:59:59 GMT\\r\\n" if conditional else ""
        result = self.run_container(
            {"BK_LOGIN_URL": "https://login.example/", "BK_SITE_URL": site},
            command=(
                "nginx -t && nginx >/tmp/nginx.log 2>&1 && "
                f"for path in {' '.join(paths)}; do "
                "printf '\\nHTTP_RESPONSE\\n'; "
                f"printf 'GET %s HTTP/1.0\\r\\nHost: localhost\\r\\n{extra_header}\\r\\n' "
                '"$path" | nc 127.0.0.1 5000; done'
            ),
        )
        self.assert_success(result)
        responses = []
        for response in result.stdout.split("\nHTTP_RESPONSE\n")[1:]:
            head, separator, body = response.partition("\n\n")
            self.assertTrue(separator, response)
            lines = head.splitlines()
            status = int(lines[0].split()[1])
            headers = {}
            for line in lines[1:]:
                name, value = line.split(":", 1)
                headers.setdefault(name.lower(), []).append(value.strip())
            responses.append((status, headers, body))
        self.assertEqual(len(responses), len(paths), result.stdout)
        return responses

    def assert_security_headers(self, headers):
        for name, value in (
            ("x-content-type-options", "nosniff"),
            ("x-frame-options", "SAMEORIGIN"),
            ("referrer-policy", "strict-origin-when-cross-origin"),
        ):
            self.assertEqual(headers.get(name), [value])

        self.assertEqual(len(headers.get("content-security-policy", [])), 1)
        directives = {}
        for directive in headers["content-security-policy"][0].split(";"):
            name, *sources = directive.split()
            directives[name] = set(sources)
        for name in ("default-src", "base-uri", "frame-ancestors"):
            self.assertEqual(directives.get(name), {"'self'"})
        for name in ("object-src", "script-src-attr"):
            self.assertEqual(directives.get(name), {"'none'"})
        # Keep current inline bootstrap scripts, without enabling eval or remote scripts.
        self.assertEqual(directives.get("script-src"), {"'self'", "'unsafe-inline'"})
        for name in ("connect-src", "frame-src"):
            self.assertEqual(directives.get(name), {"'self'", "http:", "https:"})

        self.assertEqual(len(headers.get("permissions-policy", [])), 1)
        permissions = dict(policy.strip().split("=", 1) for policy in headers["permissions-policy"][0].split(","))
        for feature in ("camera", "microphone", "geolocation", "payment", "usb"):
            self.assertEqual(permissions.get(feature), "()")

    def test_subpath_and_url_delimiters_are_replaced_literally(self):
        result = self.run_container(
            {
                "BK_SITE_URL": "/spark/",
                "BK_LOGIN_URL": "https://login.example/?next=/spark&hint=a|b",
                "BK_TEMPLATE_URL": "/templates?kind=a&kind=b|c",
            }
        )
        self.assert_success(result)
        self.assertIn('src="/spark/static/app.js"', result.stdout)
        self.assertIn("site: '/spark'", result.stdout)
        self.assertIn("https://login.example/?next=/spark&hint=a|b", result.stdout)
        self.assertIn("/templates?kind=a&kind=b|c", result.stdout)
        self.assertIn("rewrite ^/spark/(.*)$ /$1 last;", result.stdout)
        self.assertNotIn("__APP_SPARK_RT_", result.stdout)

    def test_root_defaults_to_empty_and_optional_template_to_blank_page(self):
        result = self.run_container({"BK_LOGIN_URL": "https://login.example/"})
        self.assert_success(result)
        self.assertIn('src="/static/app.js"', result.stdout)
        self.assertIn("site: ''", result.stdout)
        self.assertIn("template: 'about:blank'", result.stdout)
        self.assertNotRegex(result.stdout, r"(?m)^\s*rewrite\s")

    def test_empty_or_slash_site_omits_rewrite(self):
        for site in ("", "/"):
            with self.subTest(site=site):
                result = self.run_container({"BK_LOGIN_URL": "https://login.example/", "BK_SITE_URL": site})
                self.assert_success(result)
                self.assertIn('src="/static/app.js"', result.stdout)
                self.assertNotRegex(result.stdout, r"(?m)^\s*rewrite\s")

    def test_env_file_supports_quotes_comments_and_final_line_without_newline(self):
        result = self.run_container(
            env_file=(
                "# deployment configuration\n\n"
                "BK_SITE_URL = '/spark/'\n"
                'BK_LOGIN_URL = "https://login.example/?a=1&b=2"\n'
                "BK_TEMPLATE_URL=/templates"
            )
        )
        self.assert_success(result)
        self.assertIn("site: '/spark'", result.stdout)
        self.assertIn("login: 'https://login.example/?a=1&b=2'", result.stdout)
        self.assertIn("template: '/templates'", result.stdout)

    def test_process_environment_including_empty_values_overrides_env_file(self):
        result = self.run_container(
            {
                "BK_SITE_URL": "",
                "BK_LOGIN_URL": "https://process.example/",
                "BK_TEMPLATE_URL": "",
            },
            env_file=("BK_SITE_URL=/from-file\nBK_LOGIN_URL=https://file.example/\nBK_TEMPLATE_URL=/from-file\n"),
        )
        self.assert_success(result)
        self.assertIn("site: ''", result.stdout)
        self.assertIn("template: 'about:blank'", result.stdout)
        self.assertIn("login: 'https://process.example/'", result.stdout)
        self.assertNotIn("from-file", result.stdout)

    def test_invalid_env_file_assignment_stops_startup(self):
        result = self.run_container(
            {"BK_LOGIN_URL": "https://login.example/"},
            env_file="BK_SITE_URL /spark\n",
            command="printf 'SERVICE_STARTED\\n'",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid ENV_FILE assignment", result.stderr)
        self.assertNotIn("SERVICE_STARTED", result.stdout)

    def test_env_file_values_are_data_and_never_executed(self):
        payload = "/$(touch${IFS}/tmp/env-was-executed)"
        result = self.run_container(
            env_file=(
                "BK_LOGIN_URL=https://login.example/\n"
                f"BK_TEMPLATE_URL={payload}\n"
                "IGNORED=$(touch /tmp/unknown-was-executed)\n"
            ),
            command=(
                "test ! -e /tmp/env-was-executed && "
                "test ! -e /tmp/unknown-was-executed && "
                "cat /usr/share/nginx/html/static/app.js"
            ),
        )
        self.assert_success(result)
        self.assertIn(payload, result.stdout)

    def test_login_is_required_even_when_file_provides_value_but_env_is_empty(self):
        for env, env_file in (
            ({}, None),
            ({"BK_LOGIN_URL": ""}, "BK_LOGIN_URL=https://file.example/\n"),
            ({"BK_LOGIN_URL": "/login"}, None),
        ):
            with self.subTest(env=env):
                result = self.run_container(env, env_file=env_file)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("BK_LOGIN_URL must be an absolute HTTP(S)", result.stderr)

    def test_unsafe_string_characters_and_site_paths_are_rejected(self):
        cases = [
            ("BK_LOGIN_URL", "https://login.example/'"),
            ("BK_TEMPLATE_URL", '/templates/"'),
            ("BK_LOGIN_URL", "https://login.example/\nnext"),
            ("BK_LOGIN_URL", "https://login.example/\n"),
            ("BK_TEMPLATE_URL", "/templates/\\script"),
            ("BK_SITE_URL", "/spark space"),
            ("BK_SITE_URL", "/spark/../admin"),
            ("BK_SITE_URL", "https://spark.example/"),
            ("BK_SITE_URL", "/spark;return"),
            ("BK_TEMPLATE_URL", "//external.example/"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                env = {"BK_LOGIN_URL": "https://login.example/", key: value}
                result = self.run_container(env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(key, result.stderr)

    def test_restart_restores_pristine_assets_before_new_injection(self):
        result = self.run_container(
            {"BK_LOGIN_URL": "https://first.example/", "BK_SITE_URL": "/first"},
            raw=True,
            command=(
                f"sh {ENTRYPOINT} true && "
                "export BK_LOGIN_URL=https://second.example/ BK_SITE_URL=/second && "
                f"sh {ENTRYPOINT} sh -c 'cat /usr/share/nginx/html/index.html "
                "/usr/share/nginx/html/static/app.js'"
            ),
        )
        self.assert_success(result)
        self.assertIn('src="/second/static/app.js"', result.stdout)
        self.assertIn("login: 'https://second.example/'", result.stdout)
        self.assertNotIn("first.example", result.stdout)
        self.assertIn(
            "__APP_SPARK_RT_BK_LOGIN_URL__",
            (self.html / "static/app.js").read_text(),
        )

    def test_unknown_placeholder_stops_startup(self):
        (self.html / "static/unknown.js").write_text("__APP_SPARK_RT_UNKNOWN__")
        result = self.run_container({"BK_LOGIN_URL": "https://login.example/"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unresolved runtime placeholders", result.stderr)

    def test_injection_handles_filenames_with_spaces(self):
        (self.html / "static/runtime settings.js").write_text("const login = '__APP_SPARK_RT_BK_LOGIN_URL__';")
        result = self.run_container(
            {"BK_LOGIN_URL": "https://login.example/"},
            command="cat '/usr/share/nginx/html/static/runtime settings.js'",
        )
        self.assert_success(result)
        self.assertIn("const login = 'https://login.example/';", result.stdout)
        self.assertNotIn("__APP_SPARK_RT_", result.stdout)

    def test_final_command_preserves_arguments_exit_code_and_process_id(self):
        result = self.run_container(
            {"BK_LOGIN_URL": "https://login.example/"},
            raw=True,
            command=(
                f"exec sh {ENTRYPOINT} sh -c "
                '\'printf "pid=%s\\n" "$$"; printf "<%s>\\n" "$@"; exit 37\' '
                "command-name 'with spaces' '' '*'"
            ),
        )
        self.assertEqual(result.returncode, 37, result.stdout + result.stderr)
        self.assertIn("pid=1\n", result.stdout)
        self.assertIn("<with spaces>\n<>\n<*>\n", result.stdout)

    def test_failed_injection_cleans_temp_files_without_starting_command(self):
        (self.html / "static/unknown.js").write_text("__APP_SPARK_RT_UNKNOWN__")
        result = self.run_container(
            {"BK_LOGIN_URL": "https://login.example/", "TMPDIR": "/tmp/injection-files"},
            raw=True,
            command=(
                'mkdir "$TMPDIR" && '
                f"sh {ENTRYPOINT} touch /tmp/service-started; "
                'status=$?; test "$status" -ne 0 && '
                "test ! -e /tmp/service-started || exit 1; "
                'for file in "$TMPDIR"/*; do test ! -e "$file" || exit 1; done'
            ),
        )
        self.assert_success(result)
        self.assertIn("Unresolved runtime placeholders", result.stderr)

    def test_restart_from_subpath_to_root_removes_rewrite(self):
        result = self.run_container(
            {"BK_LOGIN_URL": "https://login.example/", "BK_SITE_URL": "/spark"},
            raw=True,
            command=(
                f"sh {ENTRYPOINT} true && "
                "export BK_SITE_URL= && "
                f"sh {ENTRYPOINT} sh -c 'nginx -t && "
                "cat /usr/share/nginx/html/index.html /etc/nginx/conf.d/default.conf'"
            ),
        )
        self.assert_success(result)
        self.assertIn('src="/static/app.js"', result.stdout)
        self.assertNotRegex(result.stdout, r"(?m)^\s*rewrite\s")

    def test_cache_policy_and_security_headers_for_root_and_subpaths(self):
        for site in ("", "/", "/spark", "/platform/spark"):
            prefix = site.rstrip("/")
            spa_content = f'src="{prefix}/static/app.js"'
            cases = [
                ("/static/app.js", 200, "login: 'https://login.example/'"),
                ("/robots.txt", 200, "User-agent: *"),
                ("/index.html", 200, spa_content),
                ("/projects/123", 200, spa_content),
                ("/", 200, spa_content),
                ("/static/app.js.map", 404, None),
                ("/static/.secret", 404, None),
                ("/static/missing.js", 404, None),
            ]
            paths = [f"{prefix}{path}" for path, _, _ in cases]
            responses = self.request_paths(site, paths)
            for (path, expected_status, expected_content), response in zip(cases, responses, strict=True):
                with self.subTest(site=site, path=path):
                    status, headers, body = response
                    self.assertEqual(status, expected_status)
                    self.assertEqual(headers.get("cache-control"), ["no-cache"])
                    self.assertNotIn("etag", headers)
                    self.assert_security_headers(headers)
                    if expected_content is not None:
                        self.assertIn(expected_content, body)
                    else:
                        self.assertNotIn("<script", body)
                        self.assertNotIn("private", body)

    def test_runtime_files_ignore_if_modified_since(self):
        for site in ("", "/spark"):
            paths = [f"{site}{path}" for path in ("/index.html", "/projects/123", "/static/app.js")]
            for path, response in zip(paths, self.request_paths(site, paths, conditional=True), strict=True):
                with self.subTest(site=site, path=path):
                    status, headers, body = response
                    self.assertEqual(status, 200)
                    self.assertEqual(headers.get("cache-control"), ["no-cache"])
                    self.assertNotIn("etag", headers)
                    self.assertTrue(body)

    def test_nginx_serves_spa_assets_health_and_rejects_private_or_api_paths(self):
        for site in ("", "/spark"):
            with self.subTest(site=site):
                result = self.run_container(
                    {"BK_LOGIN_URL": "https://login.example/", "BK_SITE_URL": site},
                    command=(
                        "nginx -t && nginx && "
                        "wget -qO- http://127.0.0.1:5000/healthz && "
                        f"wget -qO- http://127.0.0.1:5000{site}/projects/123 && "
                        f"wget -qO- http://127.0.0.1:5000{site}/static/app.js && "
                        f"for path in {site}/static/missing.js "
                        f"{site}/static/app.js.map {site}/.secret "
                        f"{site}/api-svc/projects {site}/agent/status; do "
                        "if wget -SO /tmp/response http://127.0.0.1:5000$path "
                        "2>/tmp/headers; then cat /tmp/response; exit 1; fi; "
                        "grep -q '404 Not Found' /tmp/headers || "
                        "{ cat /tmp/headers; exit 1; }; done"
                    ),
                )
                self.assert_success(result)
                self.assertIn("ok\n", result.stdout)
                self.assertIn(f'src="{site}/static/app.js"', result.stdout)
                self.assertIn("login: 'https://login.example/'", result.stdout)


if __name__ == "__main__":
    unittest.main()
