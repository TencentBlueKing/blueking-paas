## Context

You are in the apiserver repo, helping implement features, fix bugs, and refactor existing code.

## Source code

* apiserver is a REST API service implemented in Python and Django REST Framework.
* The main project in `paasng/`.
* Unit tests are placed in 'paasng/tests' directory, following pytest conventions.
* Some design notes can be found in `design_notes/`.
* When writing tests, always refer to `paasng/tests/conftest.py` for guidance on common fixtures.
* Keep business logic in the domain layer and keep API layer wiring thin.

## Coding style

* For Python files, follow PEP-8.
* For Python files, run `ruff format` to format after edits.
* In API tests, add docstrings and type hints for fixtures, especially setup fixtures.
* Preserve in-function guidance comments in test fixtures during refactors (for example setup/teardown hint comments).

### Running our tests

* Run all tests: `pytest --reuse-db -s --maxfail=1 tests/`
* Run some tests: `pytest --reuse-db -s --maxfail=1 tests/filename.py`
* ALWAYS prefer specifying test files for efficiency.
* Prioritize domain helper tests before higher-level API tests.

### Common utility libraries (avoid reinventing the wheel)

* When you need small utility functions, first check `paasng/paasng/utils/` and `paasng/paas_wl/utils/` for existing implementations before writing new code.

### File download & upload (S3/BlobStore)

* When downloading files (HTTP, S3, bkrepo, etc.) or uploading to object storage, always reuse the helpers in `paasng/paasng/platform/sourcectl/package/` and `paasng/paasng/utils/blobstore.py` instead of reinventing the wheel:
    - Download via URL (HTTP/S3/bkrepo): use `paasng.platform.sourcectl.package.downloader.download_file_via_url`, which supports both HTTP/HTTPS and BlobStore protocols.
    - Download from BlobStore by bucket+key: use `paasng.utils.blobstore.download_file_from_blob_store` instead of manually calling `make_blob_store()` then `store.download_file()`.
    - Upload: use `paasng.platform.sourcectl.package.uploader.upload_to_blob_store`, which handles upload logic and `ObjectAlreadyExists` errors. If the target bucket differs from the default `BLOBSTORE_BUCKET_AP_PACKAGES`, you may keep custom upload logic but should still create the store instance via `paasng.utils.blobstore.make_blob_store`.

### Creating new REST APIs

- Use below files as references:
    - serializers: @paasng/paasng/platform/bkapp_model/serializers/serializers.py
    - views: @paasng/paasng/platform/bkapp_model/views.py
