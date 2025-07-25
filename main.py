import hashlib
import secrets
import json
import random
import os
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
try:
    import openai
    from dotenv import load_dotenv
    load_dotenv()
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False

app = Flask(__name__)
app.secret_key = "your_secret_key"
DATA_FILE = 'debate_data.json'
LOG_FILE = 'admin_log.txt'

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    # Initialize default keys if missing
    data.setdefault("users", [])
    data.setdefault("players", [])
    data.setdefault("teams", [])
    data.setdefault("matches", [])
    data.setdefault("stories", [])
    data.setdefault("rubrics", [])
    data.setdefault("feature_toggles", {})
    data.setdefault("settings", {})
    data.setdefault("fun_content", {})

    # Feature Toggles (set defaults)
    ft = data["feature_toggles"]
    ft.setdefault("match_history_visible", True)
    ft.setdefault("player_profiles_enabled", True)
    ft.setdefault("team_stats_enabled", True)
    ft.setdefault("fun_facts_enabled", True)
    ft.setdefault("achievements_enabled", True)
    ft.setdefault("ai_practice_enabled", True)
    ft.setdefault("ai_motivation_enabled", True)

    # Settings (set defaults)
    s = data["settings"]
    s.setdefault("forum_enabled", True)
    s.setdefault("hide_elo", False)
    s.setdefault("hide_records", False)
    s.setdefault("registration_enabled", True)
    s.setdefault("require_approval", False)

    return data

def hash_password(password):
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{hashed}"

def verify_password(password, stored_hash):
    try:
        salt, hashed = stored_hash.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == hashed
    except:
        return False

def requires_admin():
    if session.get('is_backdoor_admin'):
        return True
    user_id = session.get('user_id')
    if not user_id:
        return False
    data = load_data()
    user = data['users'].get(user_id)
    return user and user.get("is_admin", False)

def requires_login():
    return bool(session.get('user_id'))

def is_banned(user_id):
    data = load_data()
    ban_info = data['banned_users'].get(user_id)
    if not ban_info:
        return False
    try:
        ban_until = datetime.fromisoformat(ban_info['until'])
        return datetime.now() < ban_until
    except ValueError:
        return True # Treat malformed date as banned

def get_current_user():
    if not session.get('user_id'):
        return None
    data = load_data()
    return data['users'].get(session['user_id'])

def log_admin_action(action, admin_username):
    with open(LOG_FILE, 'a') as f:
        timestamp = datetime.now().isoformat()
        f.write(f"[{timestamp}] {admin_username}: {action}\n")

def calculate_expected_score(elo1, elo2):
    power = (elo2 - elo1) / 400
    expected = 1 / (1 + (10 ** power))
    return expected

def update_elo_ratings(winner_elo, loser_elo, k=32):
    expected_winner = calculate_expected_score(winner_elo, loser_elo)
    expected_loser = calculate_expected_score(loser_elo, winner_elo)
    new_winner_elo = int(round(winner_elo + k * (1 - expected_winner)))
    new_loser_elo = int(round(loser_elo + k * (0 - expected_loser)))
    return new_winner_elo, new_loser_elo

def get_ai_debate_response(topic, position, user_argument, debate_format):
    if not AI_AVAILABLE:
        return "AI features are not available. Please install required packages."

    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        return "AI key not configured. Please add your OpenAI API key to Secrets."

    try:
        client = openai.OpenAI(api_key=openai_key)

        format_context = {
            'LD': "Lincoln-Douglas debate focuses on values and philosophy. Use moral frameworks and philosophical reasoning.",
            'PF': "Public Forum debate focuses on practical impacts and real-world consequences. Use evidence and statistics."
        }

        prompt = f"""You are an AI debate opponent in a {debate_format} debate format.

        Topic: {topic}
        Your position: {position}
        Format context: {format_context.get(debate_format, '')}

        The human argued: {user_argument}

        Provide a strong counter-argument that challenges their position. Be respectful but persuasive.
        Keep your response concise (2-3 paragraphs) and debate-appropriate."""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )

        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"AI error: {str(e)}"

def get_motivational_message(player_stats):
    """Generate encouraging messages for players without mentioning poor performance"""
    motivational_messages = [
        "Every great debater started with their first argument. Keep practicing!",
        "Your dedication to improving shows true championship spirit!",
        "The best debates come from passionate speakers - keep that fire burning!",
        "Remember, every champion was once a beginner who refused to give up.",
        "Your unique perspective adds valuable diversity to our team!",
        "Growth mindset is everything - you're on the right path!",
        "The debate community is stronger with committed members like you.",
        "Focus on progress, not perfection. You've got this!",
        "Every practice session brings you closer to your breakthrough moment.",
        "Your enthusiasm for debate is inspiring to see!"
    ]

    improvement_tips = [
        "Try practicing with different topics to broaden your argumentation skills.",
        "Consider recording yourself practicing - it's amazing what you'll notice!",
        "Research current events to strengthen your evidence base.",
        "Practice flowing (taking notes) during practice rounds.",
        "Work on your speaking pace and clarity for stronger delivery.",
        "Study successful debaters' techniques and adapt them to your style.",
        "Focus on one specific skill each practice session for targeted improvement.",
        "Join our AI practice sessions to get comfortable with rebuttals."
    ]

    return {
        'message': random.choice(motivational_messages),
        'tip': random.choice(improvement_tips)
    }

def is_in_bottom_percentile(player_name, data, percentile=10):
    """Check if player is in bottom percentile without revealing this fact"""
    players = data.get('players', {})
    if player_name not in players:
        return False

    player_elo = players[player_name].get('elo', 1200)
    all_elos = [p.get('elo', 1200) for p in players.values()]

    if len(all_elos) < 5:  # Not enough players for meaningful percentile
        return False

    all_elos.sort()
    cutoff_index = max(0, int(len(all_elos) * (percentile / 100)))
    cutoff_elo = all_elos[cutoff_index]

    return player_elo <= cutoff_elo

@app.route('/')
def index():
    data = load_data()
    return render_template('homepage.html',
        data=data,                
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user(),
        site_content=data.get('site_content', {})
    )

@app.route('/register', methods=['GET', 'POST', 'HEAD'])
def register():
    data = load_data()
    if not data['settings'].get('registration_enabled', True):
        flash('Registration is currently disabled.', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        player_name = request.form['player_name'].strip()
        if not all([username, email, password, player_name]):
            flash('All fields are required!', 'error')
            return render_template('register.html')
        for user_data in data['users'].values():
            if user_data['username'] == username:
                flash('Username already exists!', 'error')
                return render_template('register.html')
        if player_name not in data['players']:
            flash('Player name not found! Please contact admin to add you as a debater first.', 'error')
            return render_template('register.html')
        user_id = secrets.token_hex(16)
        data['users'][user_id] = {
            'username': username,
            'email': email,
            'password': hash_password(password),
            'player_name': player_name,
            'is_admin': False,
            'created_date': datetime.now().isoformat(),
            'approved': not data['settings'].get('require_approval', False)
        }
        save_data(data)
        if data['settings'].get('require_approval', False):
            flash('Account created! Please wait for admin approval.', 'success')
        else:
            session['user_id'] = user_id
            flash('Account created successfully!', 'success')
            return redirect(url_for('index'))
    return render_template('register.html', players=load_data()['players'])

@app.route('/login', methods=['GET', 'POST', 'HEAD'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
                # === ADMIN BACKDOOR LOGIN (not stored in JSON) ===
        if username == 'admin' and password == 'admin123':
            session['user_id'] = 'backdoor_admin'
            session['is_backdoor_admin'] = True
            with open('admin_log.txt', 'a') as log:
                log.write(f"[{datetime.now().isoformat()}] Backdoor admin login used.\n")
            flash('Logged in with developer admin access!', 'success')
            return redirect(url_for('index'))
        data = load_data()
        user_id = None
        for uid, user_data in data['users'].items():
            if user_data['username'] == username:
                user_id = uid
                break
        if user_id and verify_password(password, data['users'][user_id]['password']):
            if not data['users'][user_id].get('approved', True):
                flash('Account pending approval!', 'error')
                return render_template('login.html')
            if is_banned(user_id):
                ban_info = data['banned_users'][user_id]
                flash(f'You are banned until {ban_info["until"][:19]}. Reason: {ban_info["reason"]}', 'error')
                return render_template('login.html')
            session['user_id'] = user_id
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

@app.route('/my_account', methods=['GET', 'HEAD'])
def my_account():
    if not requires_login():
        flash('Please log in to view your account.', 'error')
        return redirect(url_for('login'))
    user = get_current_user()
    data = load_data()
    player_name = user.get('player_name')
    player_data = data['players'].get(player_name, {})

    # Add motivational content for players who might need encouragement
    motivation = None
    if player_name and is_in_bottom_percentile(player_name, data):
        motivation = get_motivational_message(player_data)

    return render_template('my_account.html',
        user=user,
        player=player_data,
        motivation=motivation,
        is_admin=requires_admin(),
        is_logged_in=True,
        current_user=user,
        site_content=data['site_content']
    )

@app.route('/ai_practice', methods=['GET', 'POST'])
def ai_practice():
    if not requires_login():
        flash('Please log in to access AI practice.', 'error')
        return redirect(url_for('login'))

    if not AI_AVAILABLE:
        flash('AI features are not available. Contact admin to set up AI functionality.', 'error')
        return redirect(url_for('index'))

    data = load_data()
    current_user = get_current_user()

    if request.method == 'POST':
        topic = request.form['topic']
        user_position = request.form['position']
        user_argument = request.form['argument']
        debate_format = request.form['format']

        # AI takes opposite position
        ai_position = 'Con' if user_position == 'Pro' else 'Pro'

        ai_response = get_ai_debate_response(topic, ai_position, user_argument, debate_format)

        # Save practice session
        practice_session = {
            'topic': topic,
            'user_position': user_position,
            'ai_position': ai_position,
            'user_argument': user_argument,
            'ai_response': ai_response,
            'format': debate_format,
            'date': datetime.now().isoformat(),
            'user': current_user['username']
        }

        if 'practice_sessions' not in data:
            data['practice_sessions'] = []
        data['practice_sessions'].append(practice_session)
        save_data(data)

        return render_template('ai_practice_result.html',
            session=practice_session,
            is_admin=requires_admin(),
            is_logged_in=True,
            current_user=current_user,
            site_content=data.get('site_content', {})
        )

    # Sample topics for practice
    sample_topics = [
        "Social media does more harm than good for teenagers",
        "Nuclear energy is essential for combating climate change",
        "Schools should eliminate standardized testing",
        "Technology companies should be broken up to prevent monopolies",
        "Space exploration funding should be redirected to earth-based problems",
        "Artificial intelligence poses an existential threat to humanity",
        "Universal basic income should be implemented nationwide",
        "Gene editing in humans should be banned"
    ]

    return render_template('ai_practice.html',
        sample_topics=sample_topics,
        is_admin=requires_admin(),
        is_logged_in=True,
        current_user=current_user,
        site_content=data.get('site_content', {})
    )
@app.route('/forum', methods=['GET', 'HEAD'])
def forum():
    data = load_data()
    posts = data.get('forum_posts', [])
    users = data.get('users', {})
    return render_template('forum.html',
                           posts=posts,
                           users=users,
                           is_admin=requires_admin(),
                           is_logged_in=requires_login(),
                           current_user=get_current_user(),
                           site_content=data.get('site_content', {})
    )

@app.route('/add_forum_post', methods=['POST'])
def add_forum_post():
    if not requires_login():
        flash("Please log in to post.", "error")
        return redirect(url_for('forum'))
    content = request.form.get('content', '').strip()
    if not content:
        flash("Post content cannot be empty.", "error")
        return redirect(url_for('forum'))
    data = load_data()
    post = {
        'id': len(data.get('forum_posts', [])) + 1,
        'author': get_current_user()['username'],
        'content': content,
        'date': datetime.now().isoformat()
    }
    data.setdefault('forum_posts', []).append(post)
    save_data(data)
    flash("Post added successfully.", "success")
    return redirect(url_for('forum'))
@app.route('/user_management', methods=['GET', 'HEAD'])
def user_management():
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))
    data = load_data()
    return render_template('user_management.html',
        users=data['users'],
        banned_users=data['banned_users'],
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user()
    )
@app.route('/admin', methods=['GET'], endpoint='admin')
def admin_dashboard():
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))

    data = load_data()
    return render_template('admin.html',
        data=data,
        is_admin=True,
        is_logged_in=True,
        current_user=get_current_user()
    )
@app.route('/admin/change_password/<user_id>', methods=['POST'])
def admin_change_password(user_id):
    if not requires_admin():
        return "Unauthorized", 403
    data = load_data()
    user = data['users'].get(user_id)
    if not user:
        return "User not found", 404
    new_password = secrets.token_urlsafe(8)
    user['password'] = hash_password(new_password)
    save_data(data)
    with open('admin_log.txt', 'a') as log_file:
        log_file.write(f"[{datetime.now().isoformat()}] Admin {session['user_id']} reset password for user {user_id}\n")
    flash(f"New password for {user['username']}: {new_password}", 'success')
    return redirect(url_for('user_management'))

@app.route('/admin/delete_user/<user_id>', methods=['POST'])
def admin_delete_user(user_id):
    if not requires_admin():
        return "Unauthorized", 403
    data = load_data()
    user = data['users'].get(user_id)
    if not user:
        return "User not found", 404
    deleted_username = user['username']
    del data['users'][user_id]
    save_data(data)
    with open('admin_log.txt', 'a') as log_file:
        log_file.write(f"[{datetime.now().isoformat()}] Admin {session['user_id']} deleted user {user_id} ({deleted_username})\n")
    flash(f"Deleted user: {deleted_username}", 'success')
    return redirect(url_for('user_management'))

@app.route('/make_admin/<user_id>', methods=['POST'])
def make_admin(user_id):
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))
    data = load_data()
    if user_id in data['users']:
        data['users'][user_id]['is_admin'] = True
        save_data(data)
        flash('Team leader powers granted.', 'success')
    else:
        flash('User not found.', 'danger')
    return redirect(url_for('user_management'))

@app.route('/remove_admin/<user_id>', methods=['POST'])
def remove_admin(user_id):
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))
    data = load_data()
    if user_id in data['users']:
        data['users'][user_id]['is_admin'] = False
        save_data(data)
        flash('Admin privileges removed!', 'success')
    return redirect(url_for('user_management'))

@app.route('/ban_user', methods=['POST'])
def ban_user():
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))
    user_id = request.form['user_id']
    ban_days = int(request.form['ban_days'])
    reason = request.form['reason'].strip()
    data = load_data()
    ban_until = datetime.now() + timedelta(days=ban_days)
    data['banned_users'][user_id] = {
        'until': ban_until.isoformat(),
        'reason': reason,
        'banned_by': session['user_id'],
        'banned_date': datetime.now().isoformat()
    }
    save_data(data)
    flash('User banned successfully!', 'success')
    return redirect(url_for('user_management'))

@app.route('/unban_user/<user_id>', methods=['POST'])
def unban_user(user_id):
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))
    data = load_data()
    if user_id in data['banned_users']:
        del data['banned_users'][user_id]
        save_data(data)
        flash('User unbanned!', 'success')
    return redirect(url_for('user_management'))

@app.route('/admin_settings', methods=['GET', 'POST'])
@requires_admin
def admin_settings():
    data = load_data()

    if request.method == 'POST':
        # Handle Feature Toggles
        toggles = data.setdefault("feature_toggles", {})
        toggles["match_history_visible"] = "match_history_visible" in request.form
        toggles["player_profiles_enabled"] = "player_profiles_enabled" in request.form
        toggles["team_stats_enabled"] = "team_stats_enabled" in request.form
        toggles["fun_facts_enabled"] = "fun_facts_enabled" in request.form
        toggles["achievements_enabled"] = "achievements_enabled" in request.form
        toggles["ai_practice_enabled"] = "ai_practice_enabled" in request.form
        toggles["ai_motivation_enabled"] = "ai_motivation_enabled" in request.form

        # Handle Core Settings
        settings = data.setdefault("settings", {})
        settings["forum_enabled"] = "forum_enabled" in request.form
        settings["hide_elo"] = "hide_elo" in request.form
        settings["hide_records"] = "hide_records" in request.form
        settings["registration_enabled"] = "registration_enabled" in request.form
        settings["require_approval"] = "require_approval" in request.form

        save_data(data)
        flash("Admin settings updated successfully.", "success")
        return redirect(url_for('admin_settings'))

    return render_template('admin_settings.html', data=data)

@app.route('/create_match_layout', methods=['GET', 'POST'])
def create_match_layout_route():
    data = load_data()
    matches = []
    format = None

    if request.method == 'POST':
        format = request.form.get('format')
        present_participants = request.form.getlist('present_participants')
        potential_judges = request.form.getlist('potential_judges')
        if format == 'LD':
            eligible_players = [name for name in present_participants if name in data['players'] and 'LD' in data['players'][name].get('formats', [])]
            sorted_players = sorted(eligible_players, key=lambda name: data['players'][name]['elo'], reverse=True)
            for i in range(0, len(sorted_players) - 1, 2):
                p1 = sorted_players[i]
                p2 = sorted_players[i+1]
                match = {
                    'participant1': (p1, data['players'][p1]),
                    'participant2': (p2, data['players'][p2]),
                    'elo_diff': abs(data['players'][p1]['elo'] - data['players'][p2]['elo']),
                    'judge': potential_judges[:1] if potential_judges else [],
                }
                matches.append(match)
        elif format == 'PF':
            eligible_teams = [name for name in present_participants if name in data['teams'] and data['teams'][name].get('format') == 'PF']
            sorted_teams = sorted(eligible_teams, key=lambda name: data['teams'][name]['elo'], reverse=True)
            for i in range(0, len(sorted_teams) - 1, 2):
                t1 = sorted_teams[i]
                t2 = sorted_teams[i+1]
                match = {
                    'participant1': (t1, data['teams'][t1]),
                    'participant2': (t2, data['teams'][t2]),
                    'elo_diff': abs(data['teams'][t1]['elo'] - data['teams'][t2]['elo']),
                    'judge': potential_judges[:1] if potential_judges else [],
                }
                matches.append(match)
        return render_template(
            'match_layout_result.html',
            matches=matches,
            format=format,
            is_admin=requires_admin(),
            is_logged_in=requires_login(),
            current_user=get_current_user()
        )
    return render_template(
        'create_match_layout.html',
        players=data['players'],
        teams=data['teams'],
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user()
    )

@app.route('/player_profile/<player_name>', methods=['GET', 'HEAD'])
def player_profile(player_name):
    """Show detailed profile for a given player"""
    data = load_data()
    player = data['players'].get(player_name)
    if not player:
        flash('Player not found!', 'error')
        return redirect(url_for('index'))
    return render_template('player_profile.html',
        player_name=player_name,
        player=player,
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user(),
        site_content=data['site_content']
    )
@app.route('/add_player', methods=['GET', 'POST'])
def add_player():
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))

    data = load_data()

    if request.method == 'POST':
        name = request.form['name'].strip()
        format_ld = 'LD' in request.form.getlist('formats')
        format_pf = 'PF' in request.form.getlist('formats')
        starting_elo = request.form.get('starting_elo', '1200')

        if not name:
            flash('Player name is required!', 'error')
            return render_template('add_player.html')

        if name in data['players']:
            flash('Player already exists!', 'error')
            return render_template('add_player.html')

        try:
            elo = int(starting_elo)
        except ValueError:
            flash('Invalid Elo rating.', 'error')
            return render_template('add_player.html')

        formats = []
        if format_ld:
            formats.append('LD')
        if format_pf:
            formats.append('PF')

        data['players'][name] = {
            'elo': elo,
            'formats': formats,
            'matches_won': 0,
            'matches_lost': 0,
            'total_matches': 0,
            'created_date': datetime.now().isoformat()
        }

        save_data(data)
        flash(f'Player {name} added successfully!', 'success')
        return redirect(url_for('user_management'))

    return render_template('add_player.html')
@app.route('/add_team', methods=['GET', 'POST', 'HEAD'])
def add_team():
    """Create a new PF team - Admin only"""
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))
    data = load_data()
    pf_players = {k: v for k, v in data['players'].items() 
                  if 'PF' in v.get('formats', []) or v.get('format') == 'PF'}
    if request.method == 'POST':
        team_name = request.form['team_name'].strip()
        member1 = request.form['member1']
        member2 = request.form['member2']
        if not team_name or member1 == member2:
            flash('Invalid team configuration!', 'error')
            return render_template('add_team.html', players=pf_players)
        if team_name in data['teams']:
            flash('Team name already exists!', 'error')
            return render_template('add_team.html', players=pf_players)

        # Error handling for non-existent players in team creation
        if member1 not in data['players'] or member2 not in data['players']:
            flash('One or more team members do not exist!', 'error')
            return render_template('add_team.html', players=pf_players)

        avg_elo = round((data['players'][member1]['elo'] + data['players'][member2]['elo']) / 2)
        data['teams'][team_name] = {
            'members': [member1, member2],
            'elo': avg_elo,
            'format': 'PF',
            'matches_won': 0,
            'matches_lost': 0,
            'total_matches': 0,
            'created_date': datetime.now().isoformat()
        }
        save_data(data)
        flash(f'Created team {team_name}!', 'success')
        return redirect(url_for('public_forum'))
    return render_template('add_team.html', players=pf_players)

@app.route('/record_match', methods=['GET', 'POST', 'HEAD'])
def record_match():
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))

    data = load_data()

    if request.method == 'POST':
        match_type = request.form['match_type']

        if match_type == 'LD':
            winner = request.form['winner']
            loser = request.form['loser']

            if winner not in data['players'] or loser not in data['players']:
                flash('One or more players not found!', 'error')
                return redirect(url_for('record_match'))

            if winner == loser:
                flash('A player cannot compete against themselves!', 'error')
                return redirect(url_for('record_match'))

            # Update elo
            winner_old_elo = data['players'][winner]['elo']
            loser_old_elo = data['players'][loser]['elo']
            new_winner_elo, new_loser_elo = update_elo_ratings(winner_old_elo, loser_old_elo)

            data['players'][winner]['elo'] = new_winner_elo
            data['players'][loser]['elo'] = new_loser_elo
            data['players'][winner]['matches_won'] += 1
            data['players'][loser]['matches_lost'] += 1
            data['players'][winner]['total_matches'] += 1
            data['players'][loser]['total_matches'] += 1

            match_record = {
                'type': 'LD',
                'winner': winner,
                'loser': loser,
                'participants': [winner, loser],
                'winner_elo_change': new_winner_elo - winner_old_elo,
                'loser_elo_change': new_loser_elo - loser_old_elo,
                'date': datetime.now().isoformat()
            }

        else:  # PF
            winning_team = request.form['winning_team']
            losing_team = request.form['losing_team']

            if winning_team not in data['teams'] or losing_team not in data['teams']:
                flash('One or more teams not found!', 'error')
                return redirect(url_for('record_match'))

            if winning_team == losing_team:
                flash('A team cannot compete against itself!', 'error')
                return redirect(url_for('record_match'))

            winner_old_elo = data['teams'][winning_team]['elo']
            loser_old_elo = data['teams'][losing_team]['elo']
            new_winner_elo, new_loser_elo = update_elo_ratings(winner_old_elo, loser_old_elo)

            data['teams'][winning_team]['elo'] = new_winner_elo
            data['teams'][losing_team]['elo'] = new_loser_elo
            data['teams'][winning_team]['matches_won'] += 1
            data['teams'][losing_team]['matches_lost'] += 1
            data['teams'][winning_team]['total_matches'] += 1
            data['teams'][losing_team]['total_matches'] += 1

            for member in data['teams'][winning_team]['members']:
                data['players'][member]['matches_won'] += 1
                data['players'][member]['total_matches'] += 1

            for member in data['teams'][losing_team]['members']:
                data['players'][member]['matches_lost'] += 1
                data['players'][member]['total_matches'] += 1

            match_record = {
                'type': 'PF',
                'winning_team': winning_team,
                'losing_team': losing_team,
                'participants': data['teams'][winning_team]['members'] + data['teams'][losing_team]['members'],
                'winner_elo_change': new_winner_elo - winner_old_elo,
                'loser_elo_change': new_loser_elo - loser_old_elo,
                'date': datetime.now().isoformat()
            }

        data['matches'].append(match_record)
        save_data(data)
        flash('Match recorded successfully!', 'success')
        return redirect(url_for('index'))

    # GET request
    return render_template(
        'record_match.html',
        data=data,
        teams=data.get('teams', {}),
        players=data.get('players', {}),
        is_logged_in=requires_login(),
        is_admin=requires_admin(),
        current_user=get_current_user(),
        site_content=data.get('site_content', {})
    )
@app.route('/edit_website', methods=['GET', 'POST'])
def edit_website():
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))

    data = load_data()
    if 'site_content' not in data:
        data['site_content'] = {}

    if request.method == 'POST':
        form = request.form
        data['site_content']['title'] = form.get('title', '').strip()
        data['site_content']['club_name'] = form.get('club_name', '').strip()
        data['site_content']['welcome_message'] = form.get('welcome_message', '').strip()
        data['site_content']['team_motto'] = form.get('team_motto', '').strip()
        data['site_content']['pf_description'] = form.get('pf_description', '').strip()
        data['site_content']['ld_description'] = form.get('ld_description', '').strip()
        save_data(data)
        flash('Website content updated successfully!', 'success')
        return redirect(url_for('edit_website'))

    return render_template('edit_website.html',
        site_content=data.get('site_content', {}),
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user()
    )
@app.route('/stories', methods=['GET', 'HEAD'])
def stories():
    """View all stories"""
    data = load_data()
    sorted_stories = sorted(data['stories'], key=lambda x: x['date'], reverse=True)
    return render_template('stories.html', 
        stories=sorted_stories, 
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user()
    )

@app.route('/add_story', methods=['GET', 'POST', 'HEAD'])
def add_story():
    """Add a new story - Admin only"""
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        if not title or not content:
            flash('Title and content are required!', 'error')
            return render_template('add_story.html')
        data = load_data()
        story = {
            'id': len(data['stories']) + 1,
            'title': title,
            'content': content,
            'date': datetime.now().isoformat(),
            'author': get_current_user()['username']
        }
        data['stories'].append(story)
        save_data(data)
        flash('Story posted successfully!', 'success')
        return redirect(url_for('stories'))
    return render_template('add_story.html')


@app.route('/add_rubric', methods=['GET', 'POST'])
def add_rubric():
    data = load_data()
    if request.method == 'POST':
        title = request.form['title'].strip()
        description = request.form['description'].strip()
        criteria = request.form['criteria'].strip()
        if not title or not criteria:
            flash('Title and criteria are required!', 'error')
            return render_template('add_rubric.html', data=data)
        rubric_id = secrets.token_hex(8)
        data['rubrics'][rubric_id] = {
            'title': title,
            'description': description,
            'criteria': criteria,
            'created_by': get_current_user()['username'],
            'created_date': datetime.now().isoformat()
        }
        save_data(data)
        flash('Rubric added!', 'success')
        return redirect(url_for('rubrics'))
    return render_template('add_rubric.html', data=data)
@app.route('/moderate_forum', methods=['GET', 'HEAD'])
def moderate_forum():
    if not requires_admin():
        flash('Admin access required!', 'error')
        return redirect(url_for('login'))

    data = load_data()
    posts = data.get('forum_posts', [])
    users = data.get('users', {})
    banned_users = data.get('banned_users', {})

    return render_template('moderate_forum.html',
        posts=posts,
        users=users,
        banned_users=banned_users,
        is_admin=True,
        is_logged_in=True,
        current_user=get_current_user()
    )


# Team profile
@app.route('/team_profile/<team_name>', methods=['GET', 'HEAD'])
def team_profile(team_name):
    """Show detailed profile for a given team"""
    data = load_data()
    team = data['teams'].get(team_name)
     # Error handling if team is not found
    if not team:
        flash('Team not found!', 'error')
        return redirect(url_for('public_forum'))
    return render_template('team_profile.html',
        team_name=team_name,
        team=team,
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user(),
        site_content=data.get('site_content', {})
    )

# Public Forum Teams
@app.route('/public_forum', methods=['GET', 'HEAD'])
def public_forum():
    data = load_data()
    teams = data['teams']
    pf_teams = {k: v for k, v in teams.items() if v.get('format') == 'PF'}
    sorted_teams = sorted(pf_teams.items(), key=lambda x: x[1]['elo'], reverse=True)
    return render_template('public_forum.html',
        teams=sorted_teams,
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user(),
        site_content=data['site_content']
    )

# Lincoln-Douglas Players
@app.route('/lincoln_douglas', methods=['GET', 'HEAD'])
def lincoln_douglas():
    data = load_data()
    ld_players = {k: v for k, v in data['players'].items() if 'LD' in v.get('formats', [])}
    sorted_players = sorted(ld_players.items(), key=lambda x: x[1]['elo'], reverse=True)
    return render_template('lincoln_douglas.html',
        players=sorted_players,
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user(),
        site_content=data['site_content']
    )

# Rubrics main view
@app.route('/rubrics', methods=['GET', 'HEAD'])
def rubrics():
    data = load_data()
    rubrics_data = data.get('rubrics', {})
    return render_template('rubrics.html',
        rubrics=rubrics_data,
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user(),
        site_content=data['site_content']
    )
@app.route('/my_rubrics', methods=['GET', 'HEAD'])
def my_rubrics():
    """View rubrics created by the currently logged-in user"""
    if not requires_login():
        flash("Please log in to view your rubrics.", "error")
        return redirect(url_for("login"))

    data = load_data()
    current_user = get_current_user()
    user_rubrics = {
        rid: rub for rid, rub in data.get("rubrics", {}).items()
        if rub.get("created_by") == current_user["username"]
    }

    return render_template('my_rubrics.html', rubrics=user_rubrics, is_admin=requires_admin(), is_logged_in=True, current_user=current_user, site_content=data['site_content'])

@app.route('/match_history', methods=['GET', 'HEAD'])
def match_history():
    """View match history"""
    data = load_data()
    if not data.get('feature_toggles', {}).get('match_history_visible', True):
        flash('Match history is currently disabled.', 'error')
        return redirect(url_for('index'))

    matches = data.get('matches', [])
    sorted_matches = sorted(matches, key=lambda x: x['date'], reverse=True)

    return render_template('match_history.html',
        matches=sorted_matches,
        is_admin=requires_admin(),
        is_logged_in=requires_login(),
        current_user=get_current_user(),
        site_content=data.get('site_content', {})
    )

@app.route('/practice_history', methods=['GET'])
def practice_history():
    """View AI practice session history"""
    if not requires_login():
        flash('Please log in to view practice history.', 'error')
        return redirect(url_for('login'))

    data = load_data()
    current_user = get_current_user()
    user_sessions = [
        session for session in data.get('practice_sessions', [])
        if session.get('user') == current_user['username']
    ]
    sorted_sessions = sorted(user_sessions, key=lambda x: x['date'], reverse=True)

    return render_template('practice_history.html',
        sessions=sorted_sessions,
        is_admin=requires_admin(),
        is_logged_in=True,
        current_user=current_user,
        site_content=data.get('site_content', {})
    )

def initialize_app():
    """Initialize the application with default data"""
    data = load_data()
    if not data['users']:
        admin_id = secrets.token_hex(16)
        data['users'][admin_id] = {
            'username': 'admin',
            'email': 'admin@school.edu',
            'password': hash_password('admin123'),
            'player_name': 'Administrator',
            'is_admin': True,
            'created_date': datetime.now().isoformat(),
            'approved': True
        }
        save_data(data)
        print("Default admin account created: username='admin', password='admin123'")

# Initialize app on import
initialize_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
