import os
import sys
import pytest

# Ensure the backend root (containing the `app` package) is on sys.path
CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app, db, socketio


class TestConfig:
    TESTING = True
    SECRET_KEY = os.environ.get('SECRET_KEY', 'test-secret')
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


@pytest.fixture()
def flask_app():
    application = create_app(TestConfig)
    with application.app_context():
        # Ensure models are imported so tables are created
        import app.models  # noqa: F401
        db.create_all()
        # Ensure Socket.IO namespaces are registered in the test app
        try:
            import importlib
            importlib.import_module('app.socketio_events')
        except Exception:
            pass
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()


@pytest.fixture()
def sio_client(flask_app):
    test_client = socketio.test_client(
        flask_app,
        flask_test_client=flask_app.test_client(),
        namespace='/ws'
    )
    yield test_client
    try:
        test_client.disconnect(namespace='/ws')
    except Exception:
        pass


