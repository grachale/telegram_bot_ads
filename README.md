# Telegram Bot Server for Scheduled Adds

The script `app/src/main.py` defines a Telegram bot that allows users to schedule and manage advertisements. It utilizes the Telebot library for the Telegram Bot API, Schedule for scheduling tasks, and psycopg2 for interacting with the PostgreSQL database.

## Features

- User authentication
- Creating and scheduling new advertisements
- Displaying user and advertisement information
- Deleting users or advertisements
- Storing adds and users in PostgreSQL database.

## Dependencies

- Telebot
- Schedule
- Psycopg2
- Tabulate

## How to Run Server

To run the script go to the `app/src` directory, provide it with a configuration file path as a command-line argument:

```bash
python main.py <config_file>
```

The configuration file should be in JSON format and include the token for the Telegram Bot API, as well as the configuration for the PostgreSQL database.
Example of usage (must be executed in the `app/src` directory):

```bash
python main.py ../configs/config.json
```

## How to Run Tests
```bash
pytest
```
Before running the server and tests, ensure you have the required dependencies installed, started PostgreSQL database with correct configuration as you have provided as a command-line argument - <config_file>.

