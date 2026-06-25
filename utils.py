import os
import sys


def clear_screen():
    '''
    This function is used to clear the terminal screen.
    '''

    if os.name == 'nt':  # For Windows
        os.system('cls')
    else:  # For Unix-based systems (Linux, macOS)
        os.system('clear')


def clear_line(line_number):
    '''Clears the line given by the line number.'''

    sys.stdout.write(f"\033[{line_number};0H\033[K")
    sys.stdout.flush()
