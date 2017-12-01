import app
import os


CONFIG_FILE = os.path.join(os.path.dirname(__file__), '/config.ini')

# Autentication and Message Integrity
SESSION_KEY = b""
DIG_SIZE = 4 # in bytes
PRESHARED_KEY = b"34c0eb22f5f08c4ad26c05a84aefd70c95fce0691ee0f967e14cf4f6a63d8ccb"
SESSION_PIN = b""
