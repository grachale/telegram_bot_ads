"""
Module for managing and interacting with user information in the 'users' table.

This module defines the User class, which represents a user entity. It includes methods for initializing
a user instance, creating a new user in the database, and retrieving user information from the database.
"""


class User:
    """
    Represents an entity for managing and interacting with user information in the 'users' table.

    Attributes:
    - user_id (int): The unique identifier for the user.
    - login (str): The login associated with the user.
    - password (str): The password associated with the user.
    - is_admin (bool): A boolean indicating whether the user has administrative privileges.

    Methods:
    - __init__(self, user=None): Initializes an instance of the User class.
    - create_new_user(self, cursor, connection): Creates a new user in the database.
    """
    def __init__(self, user=None):
        """
          Initialize an instance of the User class.

          Parameters:
          - user (tuple, optional): A tuple containing user information retrieved from the database (default=None).

          If `user` is provided, the instance is initialized with the values from the tuple.
          Otherwise, the instance is created with attributes set to None.
          """
        if user:
            self.user_id = user[0]
            self.login = user[1]
            self.password = user[2]
            self.is_admin = user[3]
        else:
            self.user_id = None
            self.login = None
            self.password = None
            self.is_admin = None

    def create_new_user(self, cursor, connection):
        """
          Creates a new user in the 'users' table of the database.

          Parameters:
          - cursor: Database cursor object.
          - connection: Database connection object.
          """
        cursor.execute(f'''
            INSERT INTO users (login, password, isAdmin) VALUES ('{self.login}', '{self.password}', {self.is_admin});
        ''')
        connection.commit()
