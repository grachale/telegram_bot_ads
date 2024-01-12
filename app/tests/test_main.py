import json
import sys
import os
import unittest

from unittest.mock import MagicMock


# Copied functions from main.py to prevent execution of main.py while importing (could not make up something else)
def load_config(path):
    """
        Load configuration data from a JSON file.

        Parameters:
        - path (str): The path to the JSON configuration file.

        Returns:
        - dict: A dictionary containing the configuration data.

        Raises:
        - FileNotFoundError: If the specified configuration file is not found.
        - json.JSONDecodeError: If there is an issue parsing the JSON data.

        The function attempts to open and read the specified JSON file at the given path.
        If successful, it parses the JSON content and returns the configuration data as a dictionary.
        """
    try:
        with open(path, encoding='utf-8') as config_file:
            config_data = json.load(config_file)
        return config_data
    except FileNotFoundError:
        print(f"Error: Configuration file '{path}' not found.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Unable to parse JSON in '{path}'.")
        sys.exit(1)


def test_load_config_valid_file():
    config_path = 'config.json'

    # Create the test configuration file
    with open(config_path, 'w') as config_file:
        config_file.write('{"token": "test_token", '
                          '"db_config": {"host": "localhost", "user": "test_user", '
                          '"password": "test_password", "database": "test_db"}}')

    # Run the function to load the configuration
    result = load_config(config_path)

    # Assert the result
    assert result == {"token": "test_token",
                      "db_config": {"host": "localhost", "user": "test_user",
                                    "password": "test_password", "database": "test_db"}}

    # Delete the created file after the test
    os.remove(config_path)


def test_load_config_file_not_found():
    config_path = 'nonexistent_config.json'

    with unittest.mock.patch('sys.exit') as mock_exit:
        load_config(config_path)

    mock_exit.assert_called_once_with(1)


def test_load_config_invalid_json():
    config_path = 'invalid_config.json'
    with open(config_path, 'w') as config_file:
        config_file.write('{"token": "test_token", '
                          '"db_config": {"host": "localhost", "user": "test_user", '
                          '"password": "test_password", "database": "test_db"')

    with unittest.mock.patch('sys.exit') as mock_exit:
        load_config(config_path)

    mock_exit.assert_called_once_with(1)
    os.remove(config_path)
