
"""
WSGI entry point for deployment
This file is used by web servers like Gunicorn or PythonAnywhere
"""

from main import app

if __name__ == "__main__":
    app.run()
