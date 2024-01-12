import sys

# I have not found another way to import module from another folder in python (spent 2 hours with that)
sys.path.insert(1, '/Users/aleksejgrachev/Desktop/Study/5th Semester/PYT/grachale')

from unittest.mock import MagicMock
from app.src.helpers.user import User


def test_init_with_user_tuple():
    user_data = (1, 'test_user', 'password123', True)
    user_instance = User(user_data)

    assert user_instance.user_id == 1
    assert user_instance.login == 'test_user'
    assert user_instance.password == 'password123'
    assert user_instance.is_admin is True


def test_init_without_user_tuple():
    user_instance = User()

    assert user_instance.user_id is None
    assert user_instance.login is None
    assert user_instance.password is None
    assert user_instance.is_admin is None


def test_create_new_user():
    mock_cursor = MagicMock()
    mock_connection = MagicMock()

    user_instance = User()
    user_instance.login = 'new_user'
    user_instance.password = 'new_password'
    user_instance.is_admin = False

    user_instance.create_new_user(mock_cursor, mock_connection)

    mock_cursor.execute.assert_called_once_with(
        "\n            INSERT INTO users (login, password, isAdmin) "
        "VALUES ('new_user', 'new_password', False);\n        "
    )
    mock_connection.commit.assert_called_once()
