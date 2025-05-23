import os
import aiohttp
from aiohttp import web
import pathlib
from dotenv import load_dotenv
import json
import secrets
import urllib.parse
import datetime
from datetime import UTC
import discord
import aiohttp_jinja2
import jinja2
from question_manager import load_questions, save_questions
from panels_manager import load_panels, save_panels
from application_components import StaffApplicationView
import math
import uuid
import logging

# Load environment variables
load_dotenv()
WEB_HOST = os.getenv('WEB_HOST', 'localhost')
WEB_PORT = int(os.getenv('WEB_PORT') or 8080)
APPS_DIRECTORY = 'storage/applications'
CLIENT_ID = os.getenv('OAUTH_CLIENT_ID')
CLIENT_SECRET = os.getenv('OAUTH_CLIENT_SECRET')
REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:8080/auth/callback')
SERVER_ID = os.getenv('SERVER_ID')

# Discord API endpoints
API_ENDPOINT = 'https://discord.com/api/v10'
TOKEN_URL = f"{API_ENDPOINT}/oauth2/token"
USER_URL = f"{API_ENDPOINT}/users/@me"

# Store bot instance
bot = None

# Ensure applications directory exists
pathlib.Path(APPS_DIRECTORY).mkdir(exist_ok=True)

# Session storage for OAuth states and user sessions
oauth_states = {}
sessions = {}

# Create panels directory if it doesn't exist
PANELS_DIRECTORY = 'storage'
pathlib.Path(PANELS_DIRECTORY).mkdir(exist_ok=True)

# Setup Jinja2 environment
def setup_jinja2(app):
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('static/templates'),
        context_processors=[aiohttp_jinja2.request_processor],
        filters={
            'json': json.dumps
        }
    )

class SimpleAccessFormatter(logging.Formatter):
    def format(self, record):
        # Format timestamp
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S,%f')[:-3]
        
        # Extract the message parts
        parts = record.getMessage().split('"')
        if len(parts) >= 3:
            # Format: timestamp - IP request status size
            ip = parts[0].split()[0]
            request = parts[1]
            status_size = parts[2].strip()
            return f"{timestamp} - {ip} {request} {status_size}"
        return f"{timestamp} - {record.getMessage()}"

# Custom access log format
access_log_format = SimpleAccessFormatter()

def auth_required(handler):
    async def wrapper(request):
        # Check session
        session_id = request.cookies.get('session_id')
        if not session_id or session_id not in sessions:
            return web.HTTPFound('/auth/login')
        
        # Get user from session
        user = sessions[session_id]
        request['user'] = user
        
        # Get server and member
        server = bot.get_guild(int(SERVER_ID))
        if not server:
            return web.Response(text="Server not found", status=404)
        
        member = server.get_member(int(user['user_id']))
        if not member:
            return web.Response(text="User not found in server", status=404)
        
        # Check if user is administrator
        is_admin = member.guild_permissions.administrator
        
        # Set user permissions
        request['user_permissions'] = {
            'is_admin': is_admin,
            'viewer_roles': []  # Will be populated in the index route
        }
        
        return await handler(request)
    return wrapper

# Authentication middleware
@web.middleware
async def auth_middleware(request, handler):
    # Allow public routes
    if request.path in ['/auth/login', '/auth/callback', '/auth/logout']:
        return await handler(request)
    
    # Check session
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in sessions:
        return web.HTTPFound('/auth/login')
    
    # Get user from session
    user = sessions[session_id]
    request['user'] = user
    
    # Get server and member
    server = bot.get_guild(int(SERVER_ID))
    if not server:
        return web.Response(text="Server not found", status=404)
    
    member = server.get_member(int(user['user_id']))
    if not member:
        return web.Response(text="User not found in server", status=404)
    
    # Check if user is administrator
    is_admin = member.guild_permissions.administrator
    
    # Set user permissions
    request['user_permissions'] = {
        'is_admin': is_admin,
        'viewer_roles': []  # Will be populated in the index route
    }
    
    # Check admin-only routes
    admin_routes = ['/positions', '/panel-creator', '/api/panels/create', '/api/questions/position/add', 
                   '/api/questions/position/delete', '/api/questions/add', '/api/questions/remove', 
                   '/api/questions/update']
    if not is_admin and request.path in admin_routes:
        return web.Response(text="Admin access required", status=403)
    
    return await handler(request)

@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPNotFound:
        return await handle_404(request)
    except Exception as ex:
        return await handler(request)

async def handle_404(request):
    # Get server info for the template
    server_info = await get_server_info()
    
    # Get user info if available
    user_info = {}
    if 'user' in request and 'user_id' in request['user']:
        user_info = await get_user_info(request['user']['user_id'])
    
    return aiohttp_jinja2.render_template('404.html', request, {
        'user': user_info,
        'is_admin': request.get('user_permissions', {}).get('is_admin', False),
        'server': server_info
    })

async def get_session(request):
    session_id = request.cookies.get('session_id')
    if not session_id or session_id not in sessions:
        raise web.HTTPUnauthorized(text='Invalid session')
    return sessions[session_id]

async def get_user_info(user_id):
    server = bot.get_guild(int(SERVER_ID))
    if not server:
        return None
    
    member = server.get_member(int(user_id))
    if not member:
        return None
    
    return {
        'id': str(member.id),
        'name': member.name,
        'avatar': member.display_avatar.url if member.display_avatar else None,
        'roles': [str(role.id) for role in member.roles],
        'is_admin': member.guild_permissions.administrator
    }

async def load_viewer_roles():
    try:
        with open('storage/viewer_roles.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

async def get_application_stats():
    try:
        applications = []
        for filename in os.listdir(APPS_DIRECTORY):
            if filename.endswith('.json'):
                with open(os.path.join(APPS_DIRECTORY, filename), 'r') as f:
                    applications.append(json.load(f))
        
        total = len(applications)
        pending = sum(1 for app in applications if app.get('status', 'pending').lower() == 'pending')
        approved = sum(1 for app in applications if app.get('status', '').lower() == 'approved')
        rejected = sum(1 for app in applications if app.get('status', '').lower() == 'rejected')
        
        return {
            'total': total,
            'pending': pending,
            'approved': approved,
            'rejected': rejected
        }
    except Exception:
        return {
            'total': 0,
            'pending': 0,
            'approved': 0,
            'rejected': 0
        }

async def load_applications():
    applications = []
    for filename in os.listdir(APPS_DIRECTORY):
        if filename.endswith('.json'):
            with open(os.path.join(APPS_DIRECTORY, filename), 'r') as f:
                app = json.load(f)
                app['id'] = filename[:-5]  # Remove .json extension
                # Ensure status field exists with default value
                if 'status' not in app:
                    app['status'] = 'pending'
                applications.append(app)
    return applications

# Routes
routes = web.RouteTableDef()

@routes.get('/auth/login')
async def auth_login(request):
    # Generate state for CSRF protection
    state = secrets.token_urlsafe(16)
    oauth_states[state] = {'created_at': datetime.datetime.now().timestamp()}
    
    # Create OAuth2 URL
    params = {
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'response_type': 'code',
        'scope': 'identify',
        'state': state,
        'prompt': 'none'
    }
    oauth_url = f"{API_ENDPOINT}/oauth2/authorize?{urllib.parse.urlencode(params)}"
    
    # Redirect to Discord OAuth
    return web.HTTPFound(oauth_url)

@routes.get('/auth/callback')
async def auth_callback(request):
    # Get the authorization code from the callback
    code = request.query.get('code')
    if not code:
        return web.Response(text='No code provided', status=400)
    
    # Exchange code for access token
    async with aiohttp.ClientSession() as session:
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }
        
        async with session.post(TOKEN_URL, data=data) as response:
            if response.status != 200:
                return web.Response(text='Failed to get access token', status=400)
            
            token_data = await response.json()
            access_token = token_data['access_token']
            
            # Get user info
            headers = {'Authorization': f'Bearer {access_token}'}
            async with session.get(USER_URL, headers=headers) as user_response:
                if user_response.status != 200:
                    return web.Response(text='Failed to get user info', status=400)
                
                user_data = await user_response.json()
                
                # Get server member info to check permissions
                server = bot.get_guild(int(SERVER_ID))
                if not server:
                    return web.Response(text='Server not found', status=404)
                
                member = server.get_member(int(user_data['id']))
                if not member:
                    return web.Response(text='User not found in server', status=404)
                
                # Check if user has ADMINISTRATOR permission or a viewer role
                is_admin = member.guild_permissions.administrator
                
                # Get viewer roles
                viewer_roles = await load_viewer_roles()
                has_viewer_role = False
                
                # Check if user has any viewer role
                for role_id in viewer_roles:
                    role = discord.utils.get(member.roles, id=int(role_id))
                    if role:
                        has_viewer_role = True
                        break
                
                # Allow access if user is admin or has viewer role
                if not is_admin and not has_viewer_role:
                    return web.Response(text='You must be an administrator or have a viewer role to access this dashboard', status=403)
                
                # Create session
                session_id = secrets.token_urlsafe(32)
                sessions[session_id] = {
                    'user_id': user_data['id'],
                    'username': user_data['username'],
                    'avatar': user_data.get('avatar'),
                    'created_at': datetime.datetime.now().timestamp()
                }
                
                # Set session cookie
                response = web.HTTPFound('/')
                response.set_cookie('session_id', session_id, httponly=True, max_age=86400)  # 24 hours
                return response

@routes.get('/auth/logout')
async def auth_logout(request):
    # Clear session
    session_id = request.cookies.get('session_id')
    if session_id and session_id in sessions:
        del sessions[session_id]
    
    # Redirect to login
    response = web.HTTPFound('/auth/login')
    response.del_cookie('session_id')
    return response

async def get_server_info():
    server = bot.get_guild(int(SERVER_ID))
    if server:
        return {
            'name': server.name,
            'icon': server.icon.url if server.icon else None,
            'member_count': server.member_count
        }
    return None

@routes.get('/')
@auth_required
async def index(request):
    session = await get_session(request)
    user_id = session['user_id']
    
    # Get server info
    server = await get_server_info()
    
    # Get user info
    user = await get_user_info(user_id)
    
    # Get application stats
    stats = await get_application_stats()
    
    # Get available positions
    positions = load_questions()
    
    # Get panels
    panels = load_panels()
    
    # Get roles for viewer selection
    guild = bot.get_guild(int(SERVER_ID))
    roles = [{'id': str(role.id), 'name': role.name} for role in guild.roles if role.name != '@everyone' and not role.managed]
    
    # Get current viewer roles
    viewer_roles = await load_viewer_roles()
    
    return aiohttp_jinja2.render_template(
        'index.html',
        request,
        {
            'server': server,
            'user': user,
            'stats': stats,
            'positions': positions,
            'panels': panels,
            'roles': roles,
            'viewer_roles': viewer_roles,
            'is_admin': request['user_permissions']['is_admin']
        }
    )

@routes.get('/applications')
@auth_required
async def applications(request):
    # Get the user from the request
    user = request['user']
    user_permissions = request['user_permissions']
    
    # Check if user is admin or has viewer role
    is_admin = user_permissions.get('is_admin', False)
    has_viewer_role = False
    
    # Get viewer roles
    viewer_roles = await load_viewer_roles()
    
    # Get server and member
    server = bot.get_guild(int(SERVER_ID))
    if server:
        member = server.get_member(int(user['user_id']))
        if member:
            # Check if the user has any of the viewer roles
            for role_id in viewer_roles:
                role = discord.utils.get(member.roles, id=int(role_id))
                if role:
                    has_viewer_role = True
                    break
    
    # If user is not admin and doesn't have viewer role, return access denied
    if not is_admin and not has_viewer_role:
        return web.Response(text="Access denied: You don't have permission to view applications", status=403)
    
    # Get query parameters
    status = request.query.get('status')
    position = request.query.get('position')
    sort = request.query.get('sort')
    page = int(request.query.get('page', 1))
    per_page = 10  # Number of applications per page
    
    # Load applications
    all_applications = await load_applications()
    
    # Filter by status if specified
    if status:
        all_applications = [app for app in all_applications if app.get('status', 'pending').lower() == status.lower()]
    
    # Filter by position if specified
    if position:
        all_applications = [app for app in all_applications if app.get('position') == position]
    
    # Sort applications by ID instead of timestamp (since we no longer store timestamp)
    if sort == 'newest':
        all_applications.sort(key=lambda app: app.get('id', ''), reverse=True)
    elif sort == 'oldest':
        all_applications.sort(key=lambda app: app.get('id', ''))
    else:
        # Default sort by newest if no sort is specified
        all_applications.sort(key=lambda app: app.get('id', ''), reverse=True)
    
    # Get total number of pages
    total_applications = len(all_applications)
    total_pages = math.ceil(total_applications / per_page)
    
    # Make sure page is within bounds
    if page < 1:
        page = 1
    elif page > total_pages and total_pages > 0:
        page = total_pages
    
    # Get applications for current page
    start_index = (page - 1) * per_page
    end_index = start_index + per_page
    applications = all_applications[start_index:end_index]
    
    # Format application data
    for app in applications:
        # Set status color
        status = app.get('status', 'pending').lower()
        if status == 'approved':
            app['status_color'] = 'success'
        elif status == 'rejected':
            app['status_color'] = 'danger'
        else:
            app['status_color'] = 'warning'  # pending
            
        # Add user avatar if available
        if server:
            member = server.get_member(int(app.get('user_id', '0')))
            if member:
                app['user_avatar'] = str(member.display_avatar.url) if member.display_avatar else None
                app['user_name'] = member.name  # Use the current Discord username
            else:
                # Fallback to stored username or "Unknown User" if member not found
                app['user_avatar'] = None
                app['user_name'] = app.get('username', 'Unknown User')
        else:
            app['user_avatar'] = None
            app['user_name'] = app.get('username', 'Unknown User')
    
    # Get positions for filter dropdown
    questions = load_questions()
    positions = list(questions.keys())
    
    # Get server info for template
    server_info = await get_server_info()
    
    # Get full user info instead of using the raw user object
    user_info = await get_user_info(user['user_id'])
    
    # Render the template
    context = {
        'applications': applications,
        'total_pages': total_pages,
        'page': page,
        'positions': positions,
        'is_admin': is_admin,
        'has_viewer_role': has_viewer_role,
        'server': server_info,
        'user': user_info  # Pass the full user info object for the template
    }
    
    # Only add filter parameters if they were explicitly provided
    if status:
        context['status'] = status
    if position:
        context['position'] = position
    if sort:
        context['sort'] = sort
    
    return aiohttp_jinja2.render_template('applications.html', request, context)

@routes.get('/positions')
@auth_required
async def questions(request):
    # Get user information from session
    user = request['user']
    
    # Get positions and questions
    positions = load_questions()
    
    # Get server info
    server = await get_server_info()
    
    # Get full user info
    user_info = await get_user_info(user['user_id'])
    
    # Get server channels and roles for the edit modal
    guild = bot.get_guild(int(SERVER_ID))
    channels = [{'id': str(channel.id), 'name': channel.name} for channel in guild.channels if isinstance(channel, discord.TextChannel)]
    roles = [{'id': str(role.id), 'name': role.name, 'color': f'#{role.color.value:06x}'} for role in guild.roles if role.name != '@everyone' and not role.managed]
    
    return aiohttp_jinja2.render_template(
        'positions.html',
        request,
        {
            'user': user_info,
            'positions': positions,
            'channels': channels,
            'roles': roles,
            'is_admin': request['user_permissions']['is_admin'],
            'server': server
        }
    )

@routes.get('/application/{id}')
@auth_required
async def application(request):
    # Get the user from the request
    user = request['user']
    user_permissions = request['user_permissions']
    
    # Check if user is admin or has viewer role
    is_admin = user_permissions.get('is_admin', False)
    has_viewer_role = False
    
    # Get viewer roles
    viewer_roles = await load_viewer_roles()
    
    # Get server and member
    server = bot.get_guild(int(SERVER_ID))
    if server:
        member = server.get_member(int(user['user_id']))
        if member:
            # Check if the user has any of the viewer roles
            for role_id in viewer_roles:
                role = discord.utils.get(member.roles, id=int(role_id))
                if role:
                    has_viewer_role = True
                    break
    
    # If user is not admin and doesn't have viewer role, return access denied
    if not is_admin and not has_viewer_role:
        return web.Response(text="Access denied: You don't have permission to view this application", status=403)
    
    # Get application ID from URL
    application_id = request.match_info['id']
    
    # Load application
    app_path = os.path.join(APPS_DIRECTORY, f'{application_id}.json')
    if not os.path.exists(app_path):
        return web.Response(text="Application not found", status=404)
    
    try:
        with open(app_path, 'r') as f:
            application = json.load(f)
    except:
        return web.Response(text="Failed to load application", status=500)
    
    # Set status color
    status = application.get('status', 'pending').lower()
    if status == 'approved':
        application['status_color'] = 'success'
    elif status == 'rejected':
        application['status_color'] = 'danger'
    else:
        application['status_color'] = 'warning'  # pending
    
    # Get server info for the template
    server_info = await get_server_info()
    
    # Get user avatar for the application
    if server:
        member = server.get_member(int(application.get('user_id', '0')))
        if member:
            application['user_avatar'] = str(member.display_avatar.url) if member.display_avatar else None
            application['user_name'] = member.name
        else:
            application['user_avatar'] = None
            application['user_name'] = application.get('user_name', 'Unknown User')
    
    # Format questions and answers for template
    questions_text = application.get('questions', [])
    answers = application.get('answers', [])
    
    application['questions'] = [
        {'question': questions_text[i], 'answer': answers[i] if i < len(answers) else ''}
        for i in range(len(questions_text))
    ]
    
    # Add application ID
    application['id'] = application_id
    
    # Get full user info instead of using the raw user object
    user_info = await get_user_info(user['user_id'])
    
    # Render the template
    return aiohttp_jinja2.render_template('application.html', request, {
        'application': application,
        'user': user_info,
        'server': server_info,
        'is_admin': is_admin
    })

@routes.delete('/api/applications/{app_id}')
async def delete_application(request):
    app_id = request.match_info['app_id']
    
    # Check if app exists
    json_path = os.path.join(APPS_DIRECTORY, f"{app_id}.json")
    
    if not os.path.exists(json_path):
        return web.json_response({'error': 'Application not found'}, status=404)
    
    try:
        os.remove(json_path)
        return web.json_response({'message': 'Application deleted successfully'})
    except Exception as e:
        return web.json_response({'error': str(e)}, status=500)

@routes.post('/api/questions/position/add')
async def add_position(request):
    try:
        data = await request.json()
        position_name = data.get('name')
        copy_from = data.get('copy_from')
        
        if not position_name:
            return web.Response(text='Position name is required', status=400)
        
        # Load existing questions
        questions = load_questions()
        
        # Check if position already exists
        if position_name in questions:
            return web.Response(text='Position already exists', status=400)
        
        # Create new position
        if copy_from and copy_from in questions:
            # Copy settings from existing position
            questions[position_name] = questions[copy_from].copy()
        else:
            # Create new position with default settings
            questions[position_name] = {
                'enabled': True,
                'questions': [],
                'log_channel': None,
                'welcome_message': f"Welcome to the {position_name} application process! Please answer the following questions to complete your application.",
                'completion_message': f"Thank you for completing your {position_name} application! Your responses have been submitted and will be reviewed soon.",
                'accepted_message': f"Congratulations! Your application for {position_name} has been accepted. Welcome to the team!",
                'denied_message': f"Thank you for applying for {position_name}. After careful consideration, we have decided not to move forward with your application at this time.",
                'ping_roles': [],
                'button_roles': [],
                'denied_removal_roles': []
            }
        
        # Save changes
        save_questions(questions)
        return web.Response(text='Position added successfully')
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.post('/api/questions/position/delete')
async def delete_position(request):
    try:
        data = await request.json()
        position = data.get('position')
        
        if not position:
            return web.Response(text='Position name is required', status=400)
        
        # Load existing questions
        questions = load_questions()
        
        # Remove position if it exists
        if position in questions:
            del questions[position]
            save_questions(questions)
            return web.Response(text='Position deleted successfully')
        else:
            return web.Response(text='Position not found', status=404)
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.post('/api/questions/add')
async def add_question(request):
    try:
        data = await request.json()
        position = data.get('position')
        question = data.get('question')
        
        if not position or not question:
            return web.Response(text='Position and question are required', status=400)
        
        # Load existing questions
        questions = load_questions()
        
        # Add question to position
        if position in questions:
            questions[position].append(question)
            save_questions(questions)
            return web.Response(text='Question added successfully')
        else:
            return web.Response(text='Position not found', status=404)
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.post('/api/questions/remove')
async def remove_question(request):
    try:
        data = await request.json()
        position = data.get('position')
        index = data.get('index')
        
        if position is None or index is None:
            return web.Response(text='Position and index are required', status=400)
        
        # Load existing questions
        questions = load_questions()
        
        # Remove question if position and index are valid
        if position in questions and 0 <= index < len(questions[position]):
            questions[position].pop(index)
            save_questions(questions)
            return web.Response(text='Question removed successfully')
        else:
            return web.Response(text='Position or index not found', status=404)
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.post('/api/questions/update')
async def update_question(request):
    try:
        data = await request.json()
        position = data.get('position')
        index = data.get('index')
        question = data.get('question')
        
        if position is None or index is None or not question:
            return web.Response(text='Position, index, and question are required', status=400)
        
        # Load existing questions
        questions = load_questions()
        
        # Update question if position and index are valid
        if position in questions and 0 <= index < len(questions[position]):
            questions[position][index] = question
            save_questions(questions)
            return web.Response(text='Question updated successfully')
        else:
            return web.Response(text='Position or index not found', status=404)
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.get('/panel-creator')
@auth_required
async def panel_creator(request):
    session = await get_session(request)
    user_id = session['user_id']
    
    # Get user info
    user = await get_user_info(user_id)
    
    # Get server info
    server = await get_server_info()
    
    # Get available positions
    positions = load_questions().keys()
    
    return aiohttp_jinja2.render_template(
        'panel_creator.html',
        request,
        {
            'user': user,
            'positions': positions,
            'is_admin': request['user_permissions']['is_admin'],
            'server': server
        }
    )

@routes.post('/api/panels/create')
async def create_panel(request):
    try:
        data = await request.json()
        
        # Validate channel ID
        try:
            channel_id = int(data['channel_id'])
        except ValueError:
            return web.Response(text="Invalid channel ID. Channel ID must be a number.", status=400)
        
        # Get the channel
        channel = bot.get_channel(channel_id)
        if not channel:
            return web.Response(text="Channel not found", status=404)
        
        # Generate a unique panel ID
        panel_id = str(uuid.uuid4())
        
        # Create the embed
        embed = discord.Embed(
            title=data['title'],
            url=data['url'] if data['url'] else None,
            description=data['description'],
            color=int(data['color'].replace('#', ''), 16)
        )
        
        # Set author if provided
        if data['author']['name']:
            embed.set_author(
                name=data['author']['name'],
                url=data['author']['url'] if data['author']['url'] else None,
                icon_url=data['author']['icon_url'] if data['author']['icon_url'] else None
            )
        
        # Set thumbnail if provided
        if data['thumbnail']['url']:
            embed.set_thumbnail(url=data['thumbnail']['url'])
        
        # Set image if provided
        if data['image']['url']:
            embed.set_image(url=data['image']['url'])
        
        # Set footer if provided
        if data['footer']['text']:
            embed.set_footer(
                text=data['footer']['text'],
                icon_url=data['footer']['icon_url'] if data['footer']['icon_url'] else None
            )
        
        # Create the select menu
        select_options = [
            discord.SelectOption(
                label=position,
                value=position,
                description=f"Apply for {position} position"
            ) for position in data['positions']
        ]
        
        # Create the view with the bot instance, select options, and panel ID
        view = StaffApplicationView(bot, select_options, panel_id)
        
        # Send the message
        message = await channel.send(embed=embed, view=view)
        
        # Register the view with the bot and message ID
        bot.add_view(view, message_id=message.id)
        
        # Save panel data
        panel_data = {
            'id': panel_id,
            'channel_id': str(channel.id),
            'message_id': str(message.id),
            'positions': data['positions']
        }
        
        # Save to panels file
        panels = load_panels()
        panels[panel_id] = panel_data
        if not save_panels(panels):
            return web.Response(text="Failed to save panel data", status=500)
        
        return web.Response(text="Panel created successfully")
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.post('/api/applications/{app_id}/status')
@auth_required
async def update_application_status(request):
    # Check if user is admin
    if not request['user_permissions']['is_admin']:
        return web.json_response({'success': False, 'error': 'Admin privileges required'}, status=403)
    
    app_id = request.match_info['app_id']
    
    # Load application
    app_path = os.path.join(APPS_DIRECTORY, f'{app_id}.json')
    if not os.path.exists(app_path):
        return web.json_response({'success': False, 'error': 'Application not found'}, status=404)
    
    try:
        data = await request.json()
        status = data.get('status')
        if status not in ['approve', 'reject']:
            return web.json_response({'success': False, 'error': 'Invalid status'}, status=400)
        
        # Load application
        with open(app_path, 'r') as f:
            application = json.load(f)
        
        # Update status (store as approved/rejected instead of approve/reject)
        application['status'] = 'approved' if status == 'approve' else 'rejected'
        application['processed_by'] = {
            'id': request['user']['user_id'],
            'name': request['user']['name'],
            'timestamp': datetime.datetime.now(UTC).isoformat()
        }
        
        # Save application
        with open(app_path, 'w') as f:
            json.dump(application, f)
        
        return web.json_response({'success': True})
    except Exception as e:
        return web.json_response({'success': False, 'error': str(e)}, status=500)

@routes.get('/api/viewer-roles')
@auth_required
async def get_viewer_roles(request):
    # Check if user is admin
    if not request['user_permissions']['is_admin']:
        return web.json_response({'success': False, 'error': 'Admin privileges required'}, status=403)
    
    # Get viewer roles
    viewer_roles = await load_viewer_roles()
    
    # Get server roles
    server = bot.get_guild(int(SERVER_ID))
    if not server:
        return web.json_response({'success': False, 'error': 'Server not found'}, status=404)
    
    # Format server roles
    server_roles = []
    for role in server.roles:
        if role.name != '@everyone' and not role.managed:
            server_roles.append({
                'id': str(role.id),
                'name': role.name,
                'color': f'#{role.color.value:06x}' if role.color.value else '#99AAB5',
                'is_viewer': str(role.id) in viewer_roles
            })
    
    # Sort roles by position
    server_roles.sort(key=lambda r: r['name'])
    
    return web.json_response({'success': True, 'roles': server_roles, 'viewer_roles': viewer_roles})

@routes.post('/api/viewer-roles/update')
@auth_required
async def update_viewer_roles(request):
    # Check if user is admin
    if not request['user_permissions']['is_admin']:
        return web.json_response({'success': False, 'error': 'Admin privileges required'}, status=403)
    
    try:
        data = await request.json()
        viewer_roles = data.get('roles', [])
        
        # Validate role IDs
        server = bot.get_guild(int(SERVER_ID))
        if not server:
            return web.json_response({'success': False, 'error': 'Server not found'}, status=404)
        
        server_role_ids = [str(role.id) for role in server.roles]
        for role_id in viewer_roles:
            if role_id not in server_role_ids:
                return web.json_response({'success': False, 'error': f'Invalid role ID: {role_id}'}, status=400)
        
        # Save viewer roles
        with open('storage/viewer_roles.json', 'w') as f:
            json.dump(viewer_roles, f)
        
        return web.json_response({'success': True})
    except Exception as e:
        return web.json_response({'success': False, 'error': str(e)}, status=500)

@routes.post('/api/questions/position/update')
@auth_required
async def update_position(request):
    try:
        data = await request.json()
        position_name = data.get('name')
        settings = data.get('settings')
        original_position = data.get('original_position', position_name)
        
        if not position_name or not settings:
            return web.Response(text='Position name and settings are required', status=400)
        
        # Load existing questions
        questions = load_questions()
        
        # Check if original position exists
        if original_position not in questions:
            return web.Response(text='Position not found', status=404)
        
        # Check if we're renaming the position
        if position_name != original_position:
            # Check if the new position name already exists
            if position_name in questions:
                return web.Response(text='A position with this name already exists', status=400)
            
            # Create new position with the new name
            questions[position_name] = questions[original_position].copy()
            
            # Delete the old position
            del questions[original_position]
        
        # Update settings
        questions[position_name].update({
            'enabled': settings.get('enabled', True),
            'questions': settings.get('questions', []),
            'log_channel': settings.get('log_channel'),
            'welcome_message': settings.get('welcome_message', f"Welcome to the {position_name} application process! Please answer the following questions to complete your application."),
            'completion_message': settings.get('completion_message', f"Thank you for completing your {position_name} application! Your responses have been submitted and will be reviewed soon."),
            'accepted_message': settings.get('accepted_message', f"Congratulations! Your application for {position_name} has been accepted. Welcome to the team!"),
            'denied_message': settings.get('denied_message', f"Thank you for applying for {position_name}. After careful consideration, we have decided not to move forward with your application at this time."),
            'ping_roles': settings.get('ping_roles', []),
            'button_roles': settings.get('button_roles', []),
            'accept_roles': settings.get('accept_roles', []),
            'reject_roles': settings.get('reject_roles', []),
            'accept_reason_roles': settings.get('accept_reason_roles', []),
            'reject_reason_roles': settings.get('reject_reason_roles', []),
            'accepted_roles': settings.get('accepted_roles', []),
            'denied_roles': settings.get('denied_roles', []),
            'restricted_roles': settings.get('restricted_roles', []),
            'required_roles': settings.get('required_roles', []),
            'accepted_removal_roles': settings.get('accepted_removal_roles', []),
            'denied_removal_roles': settings.get('denied_removal_roles', []),
            'auto_thread': settings.get('auto_thread', False),
            'time_limit': settings.get('time_limit', 60)
        })
        
        # Save changes
        save_questions(questions)
        return web.Response(text='Position updated successfully')
    except Exception as e:
        return web.Response(text=str(e), status=500)

@routes.get('/positions/edit/{position}')
@auth_required
async def edit_position(request):
    position = request.match_info['position']
    
    # Get position settings from questions file
    questions = load_questions()
    if position not in questions:
        return web.Response(text="Position not found", status=404)
    
    settings = questions[position]

    # Get channels and roles
    guild = bot.get_guild(int(SERVER_ID))
    channels = [{'id': str(channel.id), 'name': channel.name} for channel in guild.channels if isinstance(channel, discord.TextChannel)]
    roles = [{'id': str(role.id), 'name': role.name, 'color': f'#{role.color.value:06x}'} for role in guild.roles if role.name != '@everyone' and not role.managed]

    # Get user info
    user = await get_user_info(request['user']['user_id'])
    
    # Get server info
    server = await get_server_info()

    return aiohttp_jinja2.render_template('edit_position.html', 
                                         request,
                                         {
                                             'position': position,
                                             'settings': settings,
                                             'channels': channels,
                                             'roles': roles,
                                             'user': user,
                                             'is_admin': request['user_permissions']['is_admin'],
                                             'server': server
                                         })

@routes.get('/api/validate_channel/{channel_id}')
@auth_required
async def validate_channel(request):
    channel_id = request.match_info['channel_id']
    
    try:
        # Try to fetch the channel from Discord
        channel = bot.get_channel(int(channel_id))
        if channel is None:
            return web.Response(status=404, text="Channel not found")
        
        return web.Response(status=200, text="Channel exists")
    except ValueError:
        # Invalid channel ID format
        return web.Response(status=400, text="Invalid channel ID format")
    except Exception as e:
        # Any other error
        return web.Response(status=500, text=f"Error: {str(e)}")

# Create and run the app
async def start_web_server(bot_instance):
    global bot
    bot = bot_instance
    
    # Create web application
    app = web.Application(middlewares=[auth_middleware, error_middleware])
    
    # Setup Jinja2
    setup_jinja2(app)
    
    # Add routes
    app.add_routes(routes)
    
    # Add static routes
    app.router.add_static('/static', 'static')
    
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    aiohttp_logger = logging.getLogger('aiohttp.access')
    aiohttp_logger.setLevel(logging.INFO)
    
    # Create custom access logger
    access_logger = logging.getLogger('aiohttp.access')
    access_logger.setLevel(logging.INFO)
    access_logger.propagate = False
    
    # Add handler with custom format
    handler = logging.StreamHandler()
    handler.setFormatter(access_log_format)
    access_logger.addHandler(handler)
    
    # Start the server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    
    return runner, site

if __name__ == "__main__":
    import asyncio
    
    # Run the web server
    loop = asyncio.get_event_loop()
    runner, site = loop.run_until_complete(start_web_server(bot))
    
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(runner.cleanup())