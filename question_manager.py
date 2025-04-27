import os
import json
import pathlib
from dotenv import load_dotenv
import logging

# Get logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Ensure storage directory exists
pathlib.Path('storage').mkdir(exist_ok=True)
QUESTIONS_FILE = 'storage/questions.json'

def load_questions():
    if not os.path.exists(QUESTIONS_FILE):
        return {}
    
    with open(QUESTIONS_FILE, 'r') as f:
        data = json.load(f)
        # Convert old format to new format if needed
        if isinstance(data, dict) and all(isinstance(v, list) for v in data.values()):
            new_data = {}
            for position, questions in data.items():
                new_data[position] = {
                    'enabled': True,
                    'questions': questions,
                    'log_channel': None,
                    'accepted_message': 'Your application has been accepted!',
                    'denied_message': 'Your application has been denied.',
                    'restricted_roles': [],
                    'required_roles': [],
                    'accepted_roles': [],
                    'denied_roles': [],
                    'ping_roles': [],
                    'accepted_removal_roles': [],
                    'denied_removal_roles': []
                }
            save_questions(new_data)
            return new_data
        return data

def save_questions(questions):
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(QUESTIONS_FILE), exist_ok=True)
        
        with open(QUESTIONS_FILE, 'w') as f:
            json.dump(questions, f, indent=4)
        return True
    except Exception as e:
        logger.error(f"Error saving questions: {str(e)}")
        return False

def get_questions(position):
    try:
        questions = load_questions()
        if position in questions:
            if not questions[position]['enabled']:
                logger.info(f"Position {position} is disabled")
                return []
                
            if 'questions' not in questions[position]:
                logger.info(f"No 'questions' field found for position {position}")
                return []
                
            if not questions[position]['questions']:
                logger.info(f"Empty questions list for position {position}")
                return []
                
            return questions[position]['questions']
        else:
            logger.info(f"Position {position} not found in questions data")
            return []
    except Exception as e:
        logger.error(f"Error getting questions for position {position}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def add_position(position, copy_from=None):
    questions = load_questions()
    if position in questions:
        return False  # Position already exists
    
    if copy_from and copy_from in questions:
        # Copy all settings from the source position
        questions[position] = questions[copy_from].copy()
        questions[position]['questions'] = questions[copy_from]['questions'].copy()
    else:
        # Create new position with default settings
        questions[position] = {
            'enabled': True,
            'questions': [],
            'log_channel': None,
            'welcome_message': f"Welcome to the {position} application process! Please answer the following questions to complete your application.",
            'completion_message': f"Thank you for completing your {position} application! Your responses have been submitted and will be reviewed soon.",
            'accepted_message': f"Congratulations! Your application for {position} has been accepted. Welcome to the team!",
            'denied_message': f"Thank you for applying for {position}. After careful consideration, we have decided not to move forward with your application at this time.",
            'restricted_roles': [],
            'required_roles': [],
            'button_roles': [],
            'accept_roles': [],
            'reject_roles': [],
            'accept_reason_roles': [],
            'reject_reason_roles': [],
            'accepted_roles': [],
            'denied_roles': [],
            'ping_roles': [],
            'accepted_removal_roles': [],
            'denied_removal_roles': [],
            'auto_thread': False
        }
    
    return save_questions(questions)

def delete_position(position):
    questions = load_questions()
    if position in questions:
        del questions[position]
        return save_questions(questions)
    return False

def update_position_settings(position, settings):
    questions = load_questions()
    if position in questions:
        questions[position].update(settings)
        return save_questions(questions)
    return False

def add_question_to_position(position, question):
    questions = load_questions()
    if position in questions:
        questions[position]['questions'].append(question)
        return save_questions(questions)
    return False

def remove_question(position, index):
    questions = load_questions()
    if position in questions and 0 <= index < len(questions[position]['questions']):
        questions[position]['questions'].pop(index)
        return save_questions(questions)
    return False

def update_question(position, index, new_question):
    questions = load_questions()
    if position in questions and 0 <= index < len(questions[position]['questions']):
        questions[position]['questions'][index] = new_question
        return save_questions(questions)
    return False

def reorder_questions(position, new_order):
    questions = load_questions()
    if position in questions and len(new_order) == len(questions[position]['questions']):
        questions[position]['questions'] = [questions[position]['questions'][i] for i in new_order]
        return save_questions(questions)
    return False