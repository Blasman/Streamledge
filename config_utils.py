import sys
import os
import configparser

DEFAULT_CONFIG = """[Twitch]
client_id = 
client_secret = 

[Server]
port = 5008

[Browser]
width = 960
height = 570
x_pos = 240
y_pos = 240
"""

def get_script_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def validate_config(config):
    errors = []
    if not config.has_section('Twitch'):
        errors.append("Missing [Twitch] section in config.ini")
    else:
        if not config.get('Twitch', 'client_id', fallback='').strip():
            errors.append("Twitch client_id is required")
        if not config.get('Twitch', 'client_secret', fallback='').strip():
            errors.append("Twitch client_secret is required")
    if not config.has_section('Server'):
        errors.append("Missing [Server] section in config.ini")
    else:
        try:
            port = config.getint('Server', 'port', fallback=5001)
            if not (1024 <= port <= 65535):
                errors.append(f"Invalid port number {port}. Must be between 1024 and 65535")
        except ValueError:
            errors.append("Server port must be a valid integer")
    if not config.has_section('Browser'):
        errors.append("Missing [Browser] section in config.ini")
    else:
        try:
            width = config.getint('Browser', 'width', fallback=960)
            if width <= 0:
                errors.append("Browser width must be a positive integer")
        except ValueError:
            errors.append("Browser width must be a valid integer")
        try:
            height = config.getint('Browser', 'height', fallback=570)
            if height <= 0:
                errors.append("Browser height must be a positive integer")
        except ValueError:
            errors.append("Browser height must be a valid integer")
        try:
            x_pos = config.getint('Browser', 'x_pos', fallback=240)
            if x_pos < 0:
                errors.append("Browser x_pos must be a non-negative integer")
        except ValueError:
            errors.append("Browser x_pos must be a valid integer")
        try:
            y_pos = config.getint('Browser', 'y_pos', fallback=240)
            if y_pos < 0:
                errors.append("Browser y_pos must be a non-negative integer")
        except ValueError:
            errors.append("Browser y_pos must be a valid integer")
    return errors

def initialize_config(config_path):
    config = configparser.ConfigParser()
    if not os.path.exists(config_path):
        print(f"Creating default config.ini at {config_path}...")
        try:
            with open(config_path, 'w') as f:
                f.write(DEFAULT_CONFIG)
            config.read_string(DEFAULT_CONFIG)
            print("Default configuration created. Please fill in the required Twitch credentials in config.ini.")
            sys.exit(0)
        except IOError as e:
            print(f"Error creating config file: {e}")
            sys.exit(1)
    else:
        try:
            config.read(config_path)
        except configparser.Error as e:
            print(f"Error reading config file: {e}")
            sys.exit(1)
    errors = validate_config(config)
    if errors:
        print("Configuration errors found in config.ini:")
        for error in errors:
            print(f"- {error}")
        response = input("\nWould you like to overwrite with default configuration? (y/n): ").lower()
        if response == 'y':
            try:
                with open(config_path, 'w') as f:
                    f.write(DEFAULT_CONFIG)
                config.read_string(DEFAULT_CONFIG)
                print("Default configuration restored. Please fill in the required Twitch credentials in config.ini.")
                sys.exit(0)
            except IOError as e:
                print(f"Error writing config file: {e}")
                sys.exit(1)
        else:
            print("Please fix the configuration errors in config.ini")
            sys.exit(1)
    return config