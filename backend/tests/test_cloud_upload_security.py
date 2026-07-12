import pytest

from app.services import cloud_upload_service
from app.utils.errors import BusinessError


class FakeResponse:
    status_code = 200
    headers = {'Content-Length': '4', 'Content-Type': 'application/octet-stream'}

    def __init__(self):
        self.closed = False

    def iter_content(self, chunk_size):
        yield b'data'

    def close(self):
        self.closed = True


def test_cloud_upload_rejects_arbitrary_url_before_network(app, monkeypatch):
    called = False

    def should_not_call(*args, **kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(cloud_upload_service.requests, 'get', should_not_call)
    with app.app_context(), pytest.raises(BusinessError):
        cloud_upload_service.fetch_as_file_storage({
            'file_id': 'cloud://env/file',
            'temp_url': 'https://127.0.0.1/private',
            'file_name': 'scores.xlsx',
        })
    assert called is False


def test_cloud_upload_disables_redirects_bounds_download_and_closes(app, monkeypatch):
    response = FakeResponse()
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr(cloud_upload_service.requests, 'get', fake_get)
    with app.app_context():
        storage = cloud_upload_service.fetch_as_file_storage({
            'file_id': 'cloud://env/file',
            'temp_url': 'https://example.tcloudbaseapp.com/private-token',
            'file_name': 'scores.xlsx',
        }, max_size_mb=1)
        assert storage.stream.read() == b'data'
    assert captured['allow_redirects'] is False
    assert response.closed is True
