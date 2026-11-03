"""Add a moderator account, or give an existing one a new password.

This is the script to use on the live server. It touches only the admins
table: not one comment is read, changed or deleted by it, so it is safe to run
on a site full of real visitors' comments. seed.py is the opposite - it throws
every comment away - so never reach for seed.py just to add an administrator.

    python create_admin.py              asks for a username and a password
    python create_admin.py alice        asks for alice's password only

The password is typed invisibly and is asked for twice, so a typo cannot lock
you out of an account you have just made. What gets stored is not the password
but a one-way hash of it, which is why there is no "show me the password"
script to go with this one - nothing can read it back.
"""

import getpass
import sys

from werkzeug.security import generate_password_hash

import db

# Short passwords are the ones that get guessed. This is a floor, not advice:
# a long phrase you can remember beats eight random characters you cannot.
MIN_PASSWORD_LENGTH = 8


def ask_for_password():
    """Ask for the password twice and return it, or None if we should stop."""
    # getpass does not echo what is typed, so the password does not sit on the
    # screen - or in your terminal's scrollback - afterwards.
    password = getpass.getpass("Password: ")
    again = getpass.getpass("Password again: ")

    if password != again:
        print("Those two passwords are not the same. Nothing has been changed.")
        return None
    if len(password) < MIN_PASSWORD_LENGTH:
        print("That password is too short - it needs at least %d characters. "
              "Nothing has been changed." % MIN_PASSWORD_LENGTH)
        return None
    return password


if __name__ == "__main__":
    # The database may predate the admins table, so make sure it is there
    # before trying to write to it. This adds what is missing and never
    # removes anything.
    db.ensure_schema()

    # A username given on the command line, or asked for if there was none.
    if len(sys.argv) > 1:
        username = sys.argv[1].strip()
    else:
        username = input("Username: ").strip()

    if not username:
        print("A username is needed. Nothing has been changed.")
        sys.exit(1)

    password = ask_for_password()
    if password is None:
        sys.exit(1)

    created = db.create_or_update_admin(
        username, generate_password_hash(password)
    )

    if created:
        print("Created the administrator '%s'." % username)
    else:
        print("'%s' already existed - the password has been changed." % username)
    print("Database file: " + db.DATABASE_PATH)
    print("There are now %d administrator accounts." % db.count_admins())
    print("")
    print("Sign in at /admin/login")
