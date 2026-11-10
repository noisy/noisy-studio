def test_a_client_hanging_up_is_not_logged_as_a_daemon_failure(capsys):
    from noisy_studio.listener.http_api import _HTTPServer

    server = _HTTPServer.__new__(_HTTPServer)
    try:
        raise BrokenPipeError(32, 'Broken pipe')
    except BrokenPipeError:
        server.handle_error(None, ('127.0.0.1', 1))
    assert capsys.readouterr().err == ''
    try:
        raise RuntimeError('real bug')
    except RuntimeError:
        server.handle_error(None, ('127.0.0.1', 1))
    assert 'real bug' in capsys.readouterr().err
