"""Configuration for SQLAlchemy compliance test suite"""

from sqlalchemy.testing.plugin.pytestplugin import *  # noqa: F401, F403

pytest_plugins = "sqlalchemy.testing.plugin.pytestplugin"
