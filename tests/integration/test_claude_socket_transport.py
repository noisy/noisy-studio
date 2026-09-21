import json
from pathlib import Path
import socket
import tempfile
import threading
from unittest.mock import Mock

from noisy_studio.harness.claude import socket_transport
from noisy_studio.harness.claude.socket_transport import Endpoint, send

SESSION = '00000000-0000-4000-8000-000000000001'


def test_native_frame_is_newline_delimited_utf8_and_only_reports_written():
    with tempfile.TemporaryDirectory(prefix='ns-') as directory:
        path = str(Path(directory) / 'inbox')
        received = []
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(path)
            server.listen(1)
            server.settimeout(3)
            def receive():
                conn, _ = server.accept()
                with conn:
                    received.append(conn.recv(65536))
            thread = threading.Thread(target=receive)
            thread.start()

            result = send(Endpoint(SESSION, path), 'Speech: café')
            thread.join(timeout=4)

        assert (result.state, json.loads(received[0]), received[0][-1:]) == (
            'sent', {'type': 'user', 'session_id': SESSION,
                     'message': {'role': 'user', 'content': 'Speech: café'}}, b'\n',
        )


def test_missing_endpoint_is_unavailable_and_regular_file_is_rejected(tmp_path):
    regular = tmp_path / 'regular'
    regular.touch()

    assert [send(Endpoint(SESSION, str(path)), 'hello').state for path in (tmp_path / 'missing', regular)] == ['unavailable', 'rejected']


def test_partial_write_is_uncertain_and_never_retried(tmp_path, monkeypatch):
    with tempfile.TemporaryDirectory(prefix='ns-') as directory:
        path = str(Path(directory) / 'inbox')
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as server:
            server.bind(path)
            connection = Mock()
            connection.sendall.side_effect = TimeoutError()
            factory = Mock()
            factory.return_value.__enter__ = Mock(return_value=connection)
            factory.return_value.__exit__ = Mock(return_value=False)
            monkeypatch.setattr(socket_transport.socket, 'socket', factory)

            result = send(Endpoint(SESSION, path), 'hello')

        assert (result.state, connection.sendall.call_count) == ('uncertain', 1)
