
import pymysql
import os
import json
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        # Database configuration - use environment variables for production
        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', ''),
            'database': os.getenv('DB_NAME', 'debate_system'),
            'charset': 'utf8mb4',
            'autocommit': True
        }
    
    def get_connection(self):
        return pymysql.connect(**self.config)
    
    def init_database(self):
        """Initialize database tables"""
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                # Users table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(32) PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    player_name VARCHAR(100),
                    is_admin BOOLEAN DEFAULT FALSE,
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    approved BOOLEAN DEFAULT TRUE
                )
                """)
                
                # Players table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS players (
                    name VARCHAR(100) PRIMARY KEY,
                    elo INT DEFAULT 1200,
                    formats JSON,
                    matches_won INT DEFAULT 0,
                    matches_lost INT DEFAULT 0,
                    total_matches INT DEFAULT 0,
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Teams table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS teams (
                    name VARCHAR(100) PRIMARY KEY,
                    members JSON,
                    elo INT DEFAULT 1200,
                    format VARCHAR(10) DEFAULT 'PF',
                    matches_won INT DEFAULT 0,
                    matches_lost INT DEFAULT 0,
                    total_matches INT DEFAULT 0,
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Matches table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS matches (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    match_type VARCHAR(10) NOT NULL,
                    participants JSON,
                    winner VARCHAR(100),
                    loser VARCHAR(100),
                    winning_team VARCHAR(100),
                    losing_team VARCHAR(100),
                    winner_elo_change INT,
                    loser_elo_change INT,
                    date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Banned users table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS banned_users (
                    user_id VARCHAR(32) PRIMARY KEY,
                    until_date DATETIME,
                    reason TEXT,
                    banned_by VARCHAR(32),
                    banned_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Settings table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key_name VARCHAR(50) PRIMARY KEY,
                    value JSON
                )
                """)
                
                # Forum posts table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS forum_posts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    author VARCHAR(50),
                    content TEXT,
                    date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Stories table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS stories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(200),
                    content TEXT,
                    author VARCHAR(50),
                    date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Rubrics table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS rubrics (
                    id VARCHAR(16) PRIMARY KEY,
                    title VARCHAR(200),
                    description TEXT,
                    criteria TEXT,
                    created_by VARCHAR(50),
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Practice sessions table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS practice_sessions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    topic TEXT,
                    user_position VARCHAR(10),
                    ai_position VARCHAR(10),
                    user_argument TEXT,
                    ai_response TEXT,
                    format VARCHAR(10),
                    user VARCHAR(50),
                    date DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # Initialize default settings
                default_settings = {
                    'site_settings': {
                        'forum_enabled': True,
                        'hide_elo': False,
                        'hide_records': False,
                        'registration_enabled': True,
                        'require_approval': False
                    },
                    'feature_toggles': {
                        'match_history_visible': True,
                        'player_profiles_enabled': True,
                        'team_stats_enabled': True,
                        'fun_facts_enabled': True,
                        'achievements_enabled': True
                    },
                    'site_content': {
                        'title': 'Capital High School Debate System',
                        'subtitle': 'Welcome to the debate club portal!'
                    },
                    'fun_content': {
                        'club_achievements': [],
                        'fun_facts': []
                    }
                }
                
                for key, value in default_settings.items():
                    cursor.execute("""
                    INSERT IGNORE INTO settings (key_name, value) VALUES (%s, %s)
                    """, (key, json.dumps(value)))
                
        finally:
            connection.close()
    
    def load_data(self):
        """Load all data in the old JSON format for compatibility"""
        connection = self.get_connection()
        try:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                data = {
                    'users': {},
                    'players': {},
                    'teams': {},
                    'matches': [],
                    'banned_users': {},
                    'settings': {},
                    'feature_toggles': {},
                    'site_content': {},
                    'forum_posts': [],
                    'stories': [],
                    'rubrics': {},
                    'practice_sessions': [],
                    'fun_content': {}
                }
                
                # Load users
                cursor.execute("SELECT * FROM users")
                for user in cursor.fetchall():
                    data['users'][user['id']] = {
                        'username': user['username'],
                        'email': user['email'],
                        'password': user['password'],
                        'player_name': user['player_name'],
                        'is_admin': bool(user['is_admin']),
                        'created_date': user['created_date'].isoformat() if user['created_date'] else None,
                        'approved': bool(user['approved'])
                    }
                
                # Load players
                cursor.execute("SELECT * FROM players")
                for player in cursor.fetchall():
                    data['players'][player['name']] = {
                        'elo': player['elo'],
                        'formats': json.loads(player['formats']) if player['formats'] else [],
                        'matches_won': player['matches_won'],
                        'matches_lost': player['matches_lost'],
                        'total_matches': player['total_matches'],
                        'created_date': player['created_date'].isoformat() if player['created_date'] else None
                    }
                
                # Load teams
                cursor.execute("SELECT * FROM teams")
                for team in cursor.fetchall():
                    data['teams'][team['name']] = {
                        'members': json.loads(team['members']) if team['members'] else [],
                        'elo': team['elo'],
                        'format': team['format'],
                        'matches_won': team['matches_won'],
                        'matches_lost': team['matches_lost'],
                        'total_matches': team['total_matches'],
                        'created_date': team['created_date'].isoformat() if team['created_date'] else None
                    }
                
                # Load matches
                cursor.execute("SELECT * FROM matches ORDER BY date DESC")
                for match in cursor.fetchall():
                    match_data = {
                        'type': match['match_type'],
                        'participants': json.loads(match['participants']) if match['participants'] else [],
                        'winner_elo_change': match['winner_elo_change'],
                        'loser_elo_change': match['loser_elo_change'],
                        'date': match['date'].isoformat() if match['date'] else None
                    }
                    
                    if match['match_type'] == 'LD':
                        match_data['winner'] = match['winner']
                        match_data['loser'] = match['loser']
                    else:
                        match_data['winning_team'] = match['winning_team']
                        match_data['losing_team'] = match['losing_team']
                    
                    data['matches'].append(match_data)
                
                # Load banned users
                cursor.execute("SELECT * FROM banned_users")
                for ban in cursor.fetchall():
                    data['banned_users'][ban['user_id']] = {
                        'until': ban['until_date'].isoformat() if ban['until_date'] else None,
                        'reason': ban['reason'],
                        'banned_by': ban['banned_by'],
                        'banned_date': ban['banned_date'].isoformat() if ban['banned_date'] else None
                    }
                
                # Load settings
                cursor.execute("SELECT * FROM settings")
                for setting in cursor.fetchall():
                    setting_data = json.loads(setting['value']) if setting['value'] else {}
                    if setting['key_name'] == 'site_settings':
                        data['settings'] = setting_data
                    elif setting['key_name'] == 'feature_toggles':
                        data['feature_toggles'] = setting_data
                    elif setting['key_name'] == 'site_content':
                        data['site_content'] = setting_data
                    elif setting['key_name'] == 'fun_content':
                        data['fun_content'] = setting_data
                
                # Load forum posts
                cursor.execute("SELECT * FROM forum_posts ORDER BY date DESC")
                for post in cursor.fetchall():
                    data['forum_posts'].append({
                        'id': post['id'],
                        'author': post['author'],
                        'content': post['content'],
                        'date': post['date'].isoformat() if post['date'] else None
                    })
                
                # Load stories
                cursor.execute("SELECT * FROM stories ORDER BY date DESC")
                for story in cursor.fetchall():
                    data['stories'].append({
                        'id': story['id'],
                        'title': story['title'],
                        'content': story['content'],
                        'author': story['author'],
                        'date': story['date'].isoformat() if story['date'] else None
                    })
                
                # Load rubrics
                cursor.execute("SELECT * FROM rubrics")
                for rubric in cursor.fetchall():
                    data['rubrics'][rubric['id']] = {
                        'title': rubric['title'],
                        'description': rubric['description'],
                        'criteria': rubric['criteria'],
                        'created_by': rubric['created_by'],
                        'created_date': rubric['created_date'].isoformat() if rubric['created_date'] else None
                    }
                
                # Load practice sessions
                cursor.execute("SELECT * FROM practice_sessions ORDER BY date DESC")
                for session in cursor.fetchall():
                    data['practice_sessions'].append({
                        'topic': session['topic'],
                        'user_position': session['user_position'],
                        'ai_position': session['ai_position'],
                        'user_argument': session['user_argument'],
                        'ai_response': session['ai_response'],
                        'format': session['format'],
                        'user': session['user'],
                        'date': session['date'].isoformat() if session['date'] else None
                    })
                
                return data
                
        finally:
            connection.close()
    
    def save_data(self, data):
        """Save data in the database (this method provides compatibility with existing code)"""
        connection = self.get_connection()
        try:
            with connection.cursor() as cursor:
                # Clear and rebuild tables (for simplicity - in production you'd want incremental updates)
                
                # Save users
                cursor.execute("DELETE FROM users")
                for user_id, user_data in data.get('users', {}).items():
                    cursor.execute("""
                    INSERT INTO users (id, username, email, password, player_name, is_admin, created_date, approved)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        user_data.get('username'),
                        user_data.get('email'),
                        user_data.get('password'),
                        user_data.get('player_name'),
                        user_data.get('is_admin', False),
                        datetime.fromisoformat(user_data['created_date']) if user_data.get('created_date') else None,
                        user_data.get('approved', True)
                    ))
                
                # Save players
                cursor.execute("DELETE FROM players")
                for name, player_data in data.get('players', {}).items():
                    cursor.execute("""
                    INSERT INTO players (name, elo, formats, matches_won, matches_lost, total_matches, created_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        name,
                        player_data.get('elo', 1200),
                        json.dumps(player_data.get('formats', [])),
                        player_data.get('matches_won', 0),
                        player_data.get('matches_lost', 0),
                        player_data.get('total_matches', 0),
                        datetime.fromisoformat(player_data['created_date']) if player_data.get('created_date') else None
                    ))
                
                # Save teams
                cursor.execute("DELETE FROM teams")
                for name, team_data in data.get('teams', {}).items():
                    cursor.execute("""
                    INSERT INTO teams (name, members, elo, format, matches_won, matches_lost, total_matches, created_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        name,
                        json.dumps(team_data.get('members', [])),
                        team_data.get('elo', 1200),
                        team_data.get('format', 'PF'),
                        team_data.get('matches_won', 0),
                        team_data.get('matches_lost', 0),
                        team_data.get('total_matches', 0),
                        datetime.fromisoformat(team_data['created_date']) if team_data.get('created_date') else None
                    ))
                
                # Save matches
                cursor.execute("DELETE FROM matches")
                for match in data.get('matches', []):
                    cursor.execute("""
                    INSERT INTO matches (match_type, participants, winner, loser, winning_team, losing_team, 
                                       winner_elo_change, loser_elo_change, date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        match.get('type'),
                        json.dumps(match.get('participants', [])),
                        match.get('winner'),
                        match.get('loser'),
                        match.get('winning_team'),
                        match.get('losing_team'),
                        match.get('winner_elo_change'),
                        match.get('loser_elo_change'),
                        datetime.fromisoformat(match['date']) if match.get('date') else None
                    ))
                
                # Save banned users
                cursor.execute("DELETE FROM banned_users")
                for user_id, ban_data in data.get('banned_users', {}).items():
                    cursor.execute("""
                    INSERT INTO banned_users (user_id, until_date, reason, banned_by, banned_date)
                    VALUES (%s, %s, %s, %s, %s)
                    """, (
                        user_id,
                        datetime.fromisoformat(ban_data['until']) if ban_data.get('until') else None,
                        ban_data.get('reason'),
                        ban_data.get('banned_by'),
                        datetime.fromisoformat(ban_data['banned_date']) if ban_data.get('banned_date') else None
                    ))
                
                # Save settings
                settings_map = {
                    'site_settings': data.get('settings', {}),
                    'feature_toggles': data.get('feature_toggles', {}),
                    'site_content': data.get('site_content', {}),
                    'fun_content': data.get('fun_content', {})
                }
                
                cursor.execute("DELETE FROM settings")
                for key, value in settings_map.items():
                    cursor.execute("""
                    INSERT INTO settings (key_name, value) VALUES (%s, %s)
                    """, (key, json.dumps(value)))
                
                # Save forum posts
                cursor.execute("DELETE FROM forum_posts")
                for post in data.get('forum_posts', []):
                    cursor.execute("""
                    INSERT INTO forum_posts (id, author, content, date)
                    VALUES (%s, %s, %s, %s)
                    """, (
                        post.get('id'),
                        post.get('author'),
                        post.get('content'),
                        datetime.fromisoformat(post['date']) if post.get('date') else None
                    ))
                
                # Save stories
                cursor.execute("DELETE FROM stories")
                for story in data.get('stories', []):
                    cursor.execute("""
                    INSERT INTO stories (id, title, content, author, date)
                    VALUES (%s, %s, %s, %s, %s)
                    """, (
                        story.get('id'),
                        story.get('title'),
                        story.get('content'),
                        story.get('author'),
                        datetime.fromisoformat(story['date']) if story.get('date') else None
                    ))
                
                # Save rubrics
                cursor.execute("DELETE FROM rubrics")
                for rubric_id, rubric_data in data.get('rubrics', {}).items():
                    cursor.execute("""
                    INSERT INTO rubrics (id, title, description, criteria, created_by, created_date)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        rubric_id,
                        rubric_data.get('title'),
                        rubric_data.get('description'),
                        rubric_data.get('criteria'),
                        rubric_data.get('created_by'),
                        datetime.fromisoformat(rubric_data['created_date']) if rubric_data.get('created_date') else None
                    ))
                
                # Save practice sessions
                cursor.execute("DELETE FROM practice_sessions")
                for session in data.get('practice_sessions', []):
                    cursor.execute("""
                    INSERT INTO practice_sessions (topic, user_position, ai_position, user_argument, 
                                                 ai_response, format, user, date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        session.get('topic'),
                        session.get('user_position'),
                        session.get('ai_position'),
                        session.get('user_argument'),
                        session.get('ai_response'),
                        session.get('format'),
                        session.get('user'),
                        datetime.fromisoformat(session['date']) if session.get('date') else None
                    ))
                
        finally:
            connection.close()

# Global database manager instance
db_manager = DatabaseManager()
