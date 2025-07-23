
# Debate System

A comprehensive debate management system built with Flask and MySQL.

## Features

- User registration and authentication
- Player and team management
- Match recording and ELO rating system
- Lincoln-Douglas and Public Forum debate formats
- AI-powered practice sessions
- Forum and stories
- Admin panel with comprehensive management tools

## Local Development Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Set up MySQL database:
- Create a MySQL database named `debate_system`
- Update database credentials in `.env` file

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your database credentials and other settings
```

4. Initialize database:
```bash
python migrate_to_mysql.py
```

5. Run the application:
```bash
python main.py
```

## Deployment on PythonAnywhere

1. Upload your code to PythonAnywhere
2. Create a MySQL database in PythonAnywhere dashboard
3. Install requirements in PythonAnywhere console:
```bash
pip3.10 install --user -r requirements.txt
```
4. Set environment variables in PythonAnywhere web app configuration
5. Configure WSGI file to point to your Flask app
6. Run migration script to set up database
7. Reload your web app

## Environment Variables

- `DB_HOST`: MySQL database host
- `DB_USER`: MySQL database username  
- `DB_PASSWORD`: MySQL database password
- `DB_NAME`: MySQL database name
- `SECRET_KEY`: Flask secret key (change in production)
- `FLASK_DEBUG`: Set to 'False' in production
- `OPENAI_API_KEY`: OpenAI API key for AI features (optional)

## Default Admin Account

- Username: `admin`
- Password: `admin123`

**Important**: Change the admin password after first login!

## Database Schema

The application uses the following MySQL tables:
- `users`: User accounts and authentication
- `players`: Individual debate participants
- `teams`: Public Forum teams
- `matches`: Match results and history
- `banned_users`: User ban information
- `settings`: Application configuration
- `forum_posts`: Forum discussions
- `stories`: News and stories
- `rubrics`: Judging rubrics
- `practice_sessions`: AI practice session history

## Security Notes

- Change the default SECRET_KEY in production
- Use strong database passwords
- Disable debug mode in production (FLASK_DEBUG=False)
- Consider using environment-specific configuration files
