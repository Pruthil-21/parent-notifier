"""The app for a WSGI server or host, such as Vercel, which loads `app` from here."""

from parent_notifier import create_app

app = create_app()
