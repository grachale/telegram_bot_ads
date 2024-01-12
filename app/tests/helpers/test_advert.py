import sys

# I have not found another way to import module from another folder in python (spent 1 hour with that)
sys.path.insert(1, '/Users/aleksejgrachev/Desktop/Study/5th Semester/PYT/grachale')

from unittest.mock import MagicMock
from app.src.helpers.advert import Add


def test_init_with_add_tuple():
    add_data = (1, 'user', '123456', 'Test add', 'hour', '12:30')
    add_instance = Add(add_data)

    assert add_instance.id == 1
    assert add_instance.login == 'user'
    assert add_instance.chat_id == '123456'
    assert add_instance.text == 'Test add'
    assert add_instance.interval == 'hour'
    assert add_instance.time == '12:30'


def test_init_without_add_tuple():
    add_instance = Add()

    assert add_instance.id is None
    assert add_instance.login is None
    assert add_instance.chat_id is None
    assert add_instance.text is None
    assert add_instance.interval is None
    assert add_instance.time is None


def test_create_new_add():
    mock_cursor = MagicMock()
    mock_connection = MagicMock()

    add_instance = Add()
    add_instance.login = 'user'
    add_instance.chat_id = '123456'
    add_instance.text = 'Test add'
    add_instance.interval = 'hour'
    add_instance.time = '12:30'

    add_instance.create_new_add(mock_cursor, mock_connection)

    mock_cursor.execute.assert_called_once_with(
        "\n            INSERT INTO adds (login, chat_id, text, interval, time) "
        "VALUES ('user', '123456', 'Test add', 'hour', '12:30');\n        "
    )
    mock_connection.commit.assert_called_once()