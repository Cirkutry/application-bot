import os
import jinja2
import datetime
import json

# HTML template for applications
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ data.position }} Application | {{ data.user_name }}</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            background-color: #5865F2;
            color: white;
            padding: 20px;
            border-radius: 5px 5px 0 0;
            margin-bottom: 20px;
        }
        .application-info {
            background-color: #f5f5f5;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .question {
            background-color: #e9e9e9;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 15px;
        }
        .question h3 {
            margin-top: 0;
            color: #5865F2;
        }
        .answer {
            background-color: #fff;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #5865F2;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            font-size: 0.8em;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ data.position }} Application</h1>
    </div>
    
    <div class="application-info">
        <h2>Applicant Information</h2>
        <p><strong>Discord Username:</strong> {{ data.user_name }}</p>
        <p><strong>Discord ID:</strong> {{ data.user_id }}</p>
        <p><strong>Application ID:</strong> {{ app_id }}</p>
    </div>
    
    <h2>Application Responses</h2>
    {% for qa in data.questions_answers %}
    <div class="question">
        <h3>Question {{ loop.index }}</h3>
        <p>{{ qa.question }}</p>
        
        <div class="answer">
            <p>{{ qa.answer }}</p>
        </div>
    </div>
    {% endfor %}
    
    <div class="footer">
        <p>Generated on {{ generated_date }}</p>
    </div>
</body>
</html>
"""

def generate_html_application(application_data, app_id, directory):
    """
    Generates an HTML file for a staff application
    
    Args:
        application_data: Dictionary containing application information
        app_id: Unique application ID
        directory: Directory to save the HTML file
        
    Returns:
        str: Path to the generated HTML file
    """
    # Format dates
    generated_date = datetime.datetime.now().strftime("%B %d, %Y at %I:%M %p")
    
    # Render HTML using Jinja2
    template = jinja2.Template(HTML_TEMPLATE)
    html_content = template.render(
        data=application_data,
        app_id=app_id,
        generated_date=generated_date
    )
    
    # Ensure the directory exists
    os.makedirs(directory, exist_ok=True)
    
    # Write HTML file
    html_path = os.path.join(directory, f"{app_id}.html")
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return html_path