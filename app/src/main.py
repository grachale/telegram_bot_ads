"""
Telegram Bot Server for Scheduled Adds

This script defines a Telegram bot that allows users to schedule and manage advertisements.
It uses the Telebot library for Telegram Bot API, Schedule for scheduling tasks, and psycopg2 for
interacting with PostgreSQL database.

The script includes functionality for user authentication, creating and scheduling new advertisements,
displaying user and advertisement information, and deleting users or advertisements.

To run the script, provide a configuration file path as a command-line argument:
python main.py <config_file>

Author: Aleksei Grachev
"""
import signal
import sys
import threading
import time
import json

import schedule
import psycopg2
import telebot
from tabulate import tabulate
from telebot import types

from helpers.advert import Add
from helpers.user import User


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


if len(sys.argv) != 2:
    print("Usage: python main.py <config_file>")
    sys.exit(1)

# getting configuration from the inputted as CLI parameter json file
config_path = sys.argv[1]
config = load_config(config_path)

# Initialize the bot
bot = telebot.TeleBot(config.get('token'))

# Establish a connection to the database
connection = psycopg2.connect(**config.get('db_config'))

# Create a cursor object to execute SQL queries
cursor = connection.cursor()

# Current logged user (empty in the beginning)
current_user: User = User()

# dictionary for storing schedules (key - unique ID of add, value - link to schedule)
schedule_jobs = {}

# indicator of running for thread, which is responsible for sending adds
running_flag = True


# Function to send a text to the specified chat ID
def send_message(chat_id, text):
    """
     Send a text message to a specified chat using a bot.

     Parameters:
     - chat_id (int or str): The unique identifier of the chat to which the message will be sent.
     - text (str): The text content of the message.

     Sends a text message to the specified chat using the provided bot. The `chat_id` parameter
     uniquely identifies the target chat, and the `text` parameter contains the content of the message.
     """
    bot.send_message(chat_id, text)


# Start the scheduler in a separate thread
def schedule_thread_func():
    """
     Continuously run the scheduled tasks as long as the running flag is True.

     This function is designed to be executed in a separate thread. It utilizes the `schedule`
     library to run pending scheduled tasks while the `running_flag` is True. The function
     sleeps for 2 seconds between iterations to avoid excessive resource consumption.
     """
    while running_flag:
        schedule.run_pending()
        time.sleep(2)


# Create a thread for the schedule
schedule_thread = threading.Thread(target=schedule_thread_func)

# Start the thread
schedule_thread.start()

# Create a table to store users if it does not exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    login VARCHAR(255) NOT NULL,
    password VARCHAR(255) NOT NULL,
    isAdmin BOOLEAN
    );
''')

# Create a table to store adds if it does not exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS adds (
    id SERIAL PRIMARY KEY,
    login VARCHAR(255) NOT NULL,
    chat_id BIGINT NOT NULL,
    text TEXT NOT NULL,
    interval TEXT NOT NULL,
    time TEXT NOT NULL
    );
''')

# Commit all changes into database
connection.commit()


# Command to start the log in process
@bot.message_handler(commands=['start'])
def start(message):
    """
    Handle the /start command, initiating the conversation.

    Parameters:
    - message (telegram.Message): The message object representing the /start command.

    Initiates the conversation when the user sends the /start command. Sends a welcome message
    to the user and prompts them to provide their login. The conversation is then directed to
    the `process_login_step` function using `bot.register_next_step_handler`.
    """
    bot.send_message(message.chat.id, "Hello, to start please write your login:")
    bot.register_next_step_handler(message, process_login_step)


@bot.message_handler(commands=['exit'])
def log_out(message):
    """
    Handle the /exit command, logging the user out.

    Parameters:
    - message (telegram.Message): The message object representing the /exit command.

    The user is informed that they have been logged out
    and can log in again by sending the /start command.
    """
    bot.send_message(message.chat.id, "You have logged out. Write /start if you want to log in.")


@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """
     Handle callback queries triggered by inline keyboards.

     Parameters:
     - call (telegram.CallbackQuery): The callback query object representing the user's interaction.

     Responds to different callback data by initiating various actions such as creating a new user,
     adding a new post, displaying users or posts, deleting posts or users, and navigating back or exiting.
     """
    if call.data == 'new_user':
        new_user: User = User()
        # Login
        bot.send_message(call.message.chat.id, 'Write login of new user:')
        bot.register_next_step_handler(call.message, process_new_login, new_user)
    elif call.data == 'new_add':
        new_add: Add = Add()
        new_add.login = current_user.login
        bot.send_message(call.message.chat.id, 'Write chatID of the chat, where you want to post your add:')
        bot.register_next_step_handler(call.message, process_new_chat_id, new_add)
    elif call.data == 'display_users':
        cursor.execute('SELECT * FROM users')
        adds_data = cursor.fetchall()

        table = tabulate(adds_data, headers=['ID', 'Login', 'Password', 'isAdmin'],
                         tablefmt='pretty')
        bot.send_message(call.message.chat.id, table)
        delete_user_buttons(call.message)
    elif call.data == 'display_adds':
        cursor.execute(f"SELECT * FROM adds WHERE login = '{current_user.login}'")
        adds_data = cursor.fetchall()

        if adds_data:
            table = tabulate(adds_data, headers=['ID', 'Login', 'Chat ID', 'Text', 'Interval', 'Time'],
                             tablefmt='pretty')
            bot.send_message(call.message.chat.id, table)
            delete_add_buttons(call.message)
        else:
            bot.send_message(call.message.chat.id, "No previously saved adds were found.")
            user(call.message)
    elif call.data == 'delete_add':
        bot.send_message(call.message.chat.id, "Write ID of the add, which you want to be deleted.")
        bot.register_next_step_handler(call.message, delete_add)
    elif call.data == 'delete_user':
        bot.send_message(call.message.chat.id, "Write ID of the user, which you want to be deleted.")
        bot.register_next_step_handler(call.message, delete_user)
    elif call.data == 'back_user':
        user(call.message)
    elif call.data == 'back_admin':
        admin(call.message)
    elif call.data == 'exit':
        log_out(call.message)


# Process login step
def process_login_step(message):
    """
      Process the user's login during the login step of the conversation.

      Parameters:
      - message (telegram.Message): The message object representing the user's input.

      Takes the user's input as their login, checks if the user exists in the database, and proceeds
      to the next step in the login process. If the user exists, prompts the user to enter their password
      and registers the next step with `process_password_step`. If the user does not exist, informs the
      user and prompts them to try again, registering the next step with `process_login_step`.
      """
    login = message.text

    # find the user
    cursor.execute(f"SELECT * FROM users WHERE login = '{login}'")
    existing_user = cursor.fetchone()
    global current_user
    current_user = User(existing_user)

    # Check if the user exists
    if existing_user:
        bot.send_message(message.chat.id, "Great! Now, please enter your password:")
        bot.register_next_step_handler(message, process_password_step)
    else:
        bot.send_message(message.chat.id, "User with this login does not exist. Try again:")
        bot.register_next_step_handler(message, process_login_step)


# Process password step
def process_password_step(message):
    """
    Process the user's password during the login step of the conversation.

    Parameters:
    - message (telegram.Message): The message object representing the user's input.

    Takes the user's input as their password, checks if the provided password matches the stored
    password for the current user, and directs the conversation to either admin or user mode.
    If the password is incorrect, prompts the user to try again by registering the next step with
    `process_password_step`. If the password is correct, welcomes the user to either admin or user
    mode and calls the corresponding function (`admin` or `user`) to handle the next steps.
    """
    # global current_user
    password = message.text

    # if password is wrong
    if password != current_user.password:
        bot.send_message(message.chat.id, "Wrong password! Try again:")
        bot.register_next_step_handler(message, process_password_step)
        return

    # Admin mode or user one
    if current_user.is_admin:
        # admin mode
        bot.send_message(message.chat.id, "Welcome! You are in admin mode.")
        admin(message)
    else:
        # user mode
        bot.send_message(message.chat.id, "Welcome! You are in user mode.")
        user(message)


def admin(message):
    """
    Display the main menu with options using an inline keyboard.

    Parameters:
    - message (telegram.Message): The message object representing the user's interaction.

    Creates an inline keyboard with options such as displaying all registered users, creating a new user,
    and exiting the current operation. The keyboard is then sent to the user as a message.
    """
    button_display = types.InlineKeyboardButton('Display all registered users', callback_data='display_users')
    button_create = types.InlineKeyboardButton('Create new user', callback_data='new_user')
    button_exit = types.InlineKeyboardButton('Exit', callback_data='exit')

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(button_display)
    keyboard.add(button_create)
    keyboard.add(button_exit)

    bot.send_message(message.chat.id, text='Select what you want to do', reply_markup=keyboard)


def user(message):
    """
    Display the adds menu with options using an inline keyboard.

    Parameters:
    - message (telegram.Message): The message object representing the user's interaction.

    Creates an inline keyboard with options such as displaying previous adds, creating a new add,
    and exiting the current operation. The keyboard is then sent to the user as a message.
    """
    button_display = types.InlineKeyboardButton('Display previous adds', callback_data='display_adds')
    button_create = types.InlineKeyboardButton('Create new add', callback_data='new_add')
    button_exit = types.InlineKeyboardButton('Exit', callback_data='exit')

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(button_display)
    keyboard.add(button_create)
    keyboard.add(button_exit)

    bot.send_message(message.chat.id, text='Select what you want to do', reply_markup=keyboard)


def delete_add(message):
    """
    Process the deletion of an add based on the provided add ID.

    Parameters:
    - message (telegram.Message): The message object representing the user's input.

    Takes the user's input as the ID of the add to be deleted, checks if the add with the specified ID exists
    in the database, and proceeds to delete it. If the add is successfully deleted, informs the user.
    If the add with the specified ID is not found, prompts the user to try again.
    """
    id_to_delete = message.text
    cursor.execute(f"SELECT * FROM adds WHERE id = {id_to_delete};")
    adds_data = cursor.fetchall()

    if adds_data:
        # Delete the row of the add from the table
        cursor.execute(f"DELETE FROM adds WHERE id = {id_to_delete};")
        bot.send_message(message.chat.id, 'The add was successfully deleted.')
        user(message)
    else:
        bot.send_message(message.chat.id, f"Hmmm... There is no add with id - {id_to_delete}. Try again:")
        bot.register_next_step_handler(message, delete_add)


def delete_user(message):
    """
    Process the deletion of a user based on the provided user ID.

    Parameters:
    - message (telegram.Message): The message object representing the user's input.

    Takes the user's input as the ID of the user to be deleted, checks if the user with the specified ID exists
    in the database, and proceeds to delete it. If the user is successfully deleted, informs the admin.
    If the user with the specified ID is not found, prompts the admin to try again.
    """
    id_to_delete = message.text
    cursor.execute(f"SELECT * FROM users WHERE id = {id_to_delete};")
    users_data = cursor.fetchall()

    if users_data:
        # Delete the row of the add from the table
        cursor.execute(f"DELETE FROM users WHERE id = {id_to_delete};")
        bot.send_message(message.chat.id, 'The user was successfully deleted.')
        admin(message)
    else:
        bot.send_message(message.chat.id, f"Hmmm... There is no user with id - {id_to_delete}. Try again:")
        bot.register_next_step_handler(message, delete_user)


def delete_add_buttons(message):
    """
     Display inline buttons for deleting an add or going back.

     Parameters:
     - message (telegram.Message): The message object representing the user's interaction.

     Creates an inline keyboard with options such as deleting the current add or going back to the
     user menu. The keyboard is then sent to the user as a message.
     """
    button_delete = types.InlineKeyboardButton('Delete', callback_data='delete_add')
    button_back = types.InlineKeyboardButton('Back', callback_data='back_user')

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(button_delete)
    keyboard.add(button_back)

    bot.send_message(message.chat.id, text='Select what you want to do', reply_markup=keyboard)


def delete_user_buttons(message):
    """
    Display inline buttons for deleting a user or going back.

    Parameters:
    - message (telegram.Message): The message object representing the user's interaction.

    Creates an inline keyboard with options such as deleting the current user or going back to the
    admin menu. The keyboard is then sent to the user as a message.
    """
    button_delete = types.InlineKeyboardButton('Delete', callback_data='delete_user')
    button_back = types.InlineKeyboardButton('Back', callback_data='back_admin')

    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(button_delete)
    keyboard.add(button_back)

    bot.send_message(message.chat.id, text='Select what you want to do', reply_markup=keyboard)


# Process new chatID step
def process_new_chat_id(message, new_add):
    """
    Process the chat ID during the creation of a new add.

    Parameters:
    - message (telegram.Message): The message object representing the user's input.
    - new_add: An instance of the Add class representing the new add being created.

    Takes the user's input as the chat ID for the new add and proceeds to the next step in the creation process.
    Prompts the user to enter the text for the new add and registers the next step with `process_new_text`.
    """
    new_add.chat_id = message.text
    bot.send_message(message.chat.id, 'Write the text for your add:')
    bot.register_next_step_handler(message, process_new_text, new_add)


# Process new text step
def process_new_text(message, new_add):
    """
    Process the text during the creation of a new add.

    Parameters:
    - message (telegram.Message): The message object representing the user's input.
    - new_add: An instance of the Add class representing the new add being created.

    Takes the user's input as the text for the new add and proceeds to the next step in the creation process.
    Prompts the user to enter the interval for sending the add and registers the next step with `process_new_interval`.
    """
    new_add.text = message.text
    bot.send_message(message.chat.id, 'Write the interval of sending the add (day, hour, minute):')
    bot.register_next_step_handler(message, process_new_interval, new_add)


# Process new interval
def process_new_interval(message, new_add):
    """
    Process the interval during the creation of a new add.

    Parameters:
    - message (telegram.Message): The message object representing the user's input.
    - new_add: An instance of the Add class representing the new add being created.

    Takes the user's input as the interval for sending the new add and proceeds to the next step in the creation process.
    Depending on the selected interval (day, hour, minute), prompts the user to enter the time for sending the add.
    Registers the next step with `process_new_time_day`, `process_new_time_hour`, or `process_new_time_minute` accordingly.
    """
    interval = message.text.lower()
    new_add.interval = interval
    if interval == 'day':
        bot.send_message(message.chat.id, "What time does add must be sent at? (format - 'hh:mm')")
        bot.register_next_step_handler(message, process_new_time_day, new_add)
    elif interval == 'hour':
        bot.send_message(message.chat.id, "What time does add must be sent at? (format - ':mm')")
        bot.register_next_step_handler(message, process_new_time_hour, new_add)
    elif interval == 'minute':
        bot.send_message(message.chat.id, "What time does add must be sent at? (format - ':ss')")
        bot.register_next_step_handler(message, process_new_time_minute, new_add)
    else:
        bot.send_message(message.chat.id, 'Hmm... Try again:')
        bot.register_next_step_handler(message, process_new_interval, new_add)


def process_new_time_day(message, new_add):
    """
    Process the time during the creation of a new add with a daily interval.

    Parameters:
    - message (telegram.Message): The message object representing the user's input.
    - new_add: An instance of the Add class representing the new add being created.

    Takes the user's input as the time for sending the new add with a daily interval.
    Writes the new add to the database, schedules the message to be sent every day at the specified time,
    and informs the user that the add was successfully saved. Finally, returns to the user menu.
    """
    new_add.time = message.text

    # Writing to db
    new_add.create_new_add(cursor=cursor, connection=connection)

    # Schedule the message to be sent every day at a specific time (replace with your desired time)
    job = schedule.every().day.at(new_add.time).do(send_message, new_add.chat_id, new_add.text)

    cursor.execute('SELECT MAX(id) FROM adds')
    schedule_jobs[cursor.fetchone()[0]] = job

    bot.send_message(message.chat.id, 'Your add was successfully saved!')

    # Return to user menu
    user(message)


def process_new_time_hour(message, new_add):
    """
      Process the time during the creation of a new add with an hourly interval.

      Parameters:
      - message (telegram.Message): The message object representing the user's input.
      - new_add: An instance of the Add class representing the new add being created.

      Takes the user's input as the time for sending the new add with an hourly interval.
      Writes the new add to the database, schedules the message to be sent every hour at the specified time,
      and informs the user that the add was successfully saved. Finally, returns to the user menu.
      """
    new_add.time = message.text

    # Writing to db
    new_add.create_new_add(cursor=cursor, connection=connection)

    # Schedule the message to be sent every day at a specific time (replace with your desired time)
    job = schedule.every().hour.at(new_add.time).do(send_message, new_add.chat_id, new_add.text)

    cursor.execute('SELECT MAX(id) FROM adds')
    schedule_jobs[cursor.fetchone()[0]] = job

    bot.send_message(message.chat.id, 'Your add was successfully saved!')

    # Return to user menu
    user(message)


# Process new time step
def process_new_time_minute(message, new_add):
    """
      Process the time during the creation of a new add with a minute interval.

      Parameters:
      - message (telegram.Message): The message object representing the user's input.
      - new_add: An instance of the Add class representing the new add being created.

      Takes the user's input as the time for sending the new add with a minute interval.
      Writes the new add to the database, schedules the message to be sent every minute at the specified time,
      and informs the user that the add was successfully saved. Finally, returns to the user menu.
      """
    new_add.time = message.text

    # Writing to db
    new_add.create_new_add(cursor=cursor, connection=connection)

    # Schedule the message to be sent every day at a specific time (replace with your desired time)
    job = schedule.every().minute.at(new_add.time).do(send_message, new_add.chat_id, new_add.text)

    cursor.execute('SELECT MAX(id) FROM adds')
    schedule_jobs[cursor.fetchone()[0]] = job

    bot.send_message(message.chat.id, 'Your add was successfully saved!')

    # Return to user menu
    user(message)


def process_new_login(message, new_user):
    """
      Process the login during the creation of a new user.

      Parameters:
      - message (telegram.Message): The message object representing the user's input.
      - new_user: An instance of the User class representing the new user being created.

      Takes the user's input as the login for the new user, checks if a user with the same login already exists,
      and prompts the user to try again if the login is already taken. If the login is unique, proceeds to the next step
      in the creation process by asking the user to provide a password.
      """
    new_user.login = message.text
    cursor.execute(f"SELECT * FROM users WHERE login = '{new_user.login}'")
    fetched_user = cursor.fetchone()
    if fetched_user:
        bot.send_message(message.chat.id, 'User with this login already exists. Try again:')
        bot.register_next_step_handler(message, process_new_login, new_user)
    # Password
    bot.send_message(message.chat.id, 'Great! Write a password:')
    bot.register_next_step_handler(message, process_new_password, new_user)


def process_new_password(message, new_user):
    """
     Process the password during the creation of a new user.

     Parameters:
     - message (telegram.Message): The message object representing the user's input.
     - new_user: An instance of the User class representing the new user being created.

     Takes the user's input as the password for the new user and proceeds to the next step
     in the creation process by asking whether the user is an admin or not.
     """
    new_user.password = message.text
    bot.send_message(message.chat.id, 'Is it admin? (Yes or No)')
    bot.register_next_step_handler(message, process_new_is_admin, new_user)


def process_new_is_admin(message, new_user):
    """
    Process whether the new user is an admin during user creation.

    Parameters:
    - message (telegram.Message): The message object representing the user's input.
    - new_user: An instance of the User class representing the new user being created.

    Takes the user's input regarding whether the new user is an admin or not. If the answer is 'yes',
    sets the user's admin status to True; if 'no', sets it to False. If the input is not recognized,
    prompts the user to try again. Finally, writes the new user to the database and informs the user
    that the new user has been successfully created.
    """
    answer = message.text.lower()
    if answer == 'yes':
        new_user.is_admin = True
    elif answer == 'no':
        new_user.is_admin = False
    else:
        bot.send_message(message.chat.id, 'Hmmm... Try again:')
        bot.register_next_step_handler(message, process_new_is_admin, new_user)
        return

    new_user.create_new_user(cursor=cursor, connection=connection)
    bot.send_message(message.chat.id, 'New user has been created.')
    admin(message)


# Define a function to handle the interrupt signal and clean everything up
def clean_up(sig=None, frame=None):
    """
    Perform clean-up tasks when the server stops working.

    Parameters:
    - sig: Signal number (default=None).
    - frame: Current stack frame (default=None).

    Stops the server, cleans up resources, and exits the program gracefully. This function is typically called
    when a termination signal (such as SIGINT or SIGTERM) is received. It sets a flag (`running_flag`) to stop
    the main thread and waits for the thread to finish. It also stops the Telegram bot polling, closes the database
    connection, and exits the program with a status code of 0.
    """
    print('\nServer stops working.')
    # Clean up resources
    # Set the flag to stop the thread
    global running_flag
    running_flag = False

    # Wait for the thread to finish
    schedule_thread.join()

    bot.stop_polling()
    cursor.close()
    connection.close()
    sys.exit(0)


# Register the signal handler
signal.signal(signal.SIGINT, clean_up)

if __name__ == '__main__':
    try:
        print('Server starts working.')
        bot.infinity_polling()
    except Exception as e:
        print(f"An error occurred: {e}")
        clean_up()
