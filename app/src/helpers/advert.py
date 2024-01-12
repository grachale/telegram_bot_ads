"""
Module for managing and interacting with the 'adds' table in the database.

This module defines the Add class, which represents an add entity. It includes methods for initializing
an add instance, creating a new addvert in the database, and retrieving add information from the database
"""


class Add:
    """
      Represents an entity for managing and interacting with add information in the 'adds' table.

      Attributes:
      - id (int): The unique identifier for the add.
      - login (str): The login associated with the add.
      - chat_id (str): The chat ID where the add will be posted.
      - text (str): The text content of the add.
      - interval (str): The interval at which the add should be sent (e.g., 'day', 'hour', 'minute').
      - time (str): The specific time at which the add should be sent (formatted as 'hh:mm').

      Methods:
      - __init__(self, add=None): Initializes an instance of the Add class.
      - create_new_add(self, cursor, connection): Creates a new addvert in the database.
      """
    def __init__(self, add=None):
        """
         Initialize an instance of the Add class.

         Parameters:
         - add (tuple, optional): A tuple containing add information retrieved from the database (default=None).

         If `add` is provided, the instance is initialized with the values from the tuple.
         Otherwise, the instance is created with attributes set to None.
         """
        if add:
            self.id = add[0]
            self.login = add[1]
            self.chat_id = add[2]
            self.text = add[3]
            self.interval = add[4]
            self.time = add[5]
        else:
            self.id = None
            self.login = None
            self.chat_id = None
            self.text = None
            self.interval = None
            self.time = None

    def create_new_add(self, cursor, connection):
        """
          Create a new addvert in the database.

          Parameters:
          - cursor: Database cursor object.
          - connection: Database connection object.

          Inserts a new add into the 'adds' table with the attributes of the current instance.
          Commits the changes to the database.
          """
        cursor.execute(f'''
            INSERT INTO adds (login, chat_id, text, interval, time) VALUES ('{self.login}', '{self.chat_id}', '{self.text}', '{self.interval}', '{self.time}');
        ''')
        connection.commit()
