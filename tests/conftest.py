import pytest

from voice_demo.config.loader import load_config


@pytest.fixture
def app_config():
    return load_config("config/app.yaml")
