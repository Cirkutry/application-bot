const data = {
    position: position,
    questions: questions,
    log_channel: logChannel,
    welcome_message: document.getElementById('welcomeMessage').value,
    completion_message: document.getElementById('completionMessage').value,
    accepted_message: document.getElementById('acceptedMessage').value,
    denied_message: document.getElementById('deniedMessage').value,
    ping_roles: pingRoles,
    button_roles: buttonRoles,
    accepted_roles: acceptedRoles,
    denied_roles: deniedRoles
}; 

function submitEditPosition(event) {
    event.preventDefault();
    
    const position = document.getElementById('editPositionName').value;
    const enabled = document.getElementById('positionEnabled').checked;
    const logChannel = document.getElementById('logChannel').value;
    const welcomeMessage = document.getElementById('welcomeMessage').value;
    const completionMessage = document.getElementById('completionMessage').value;
    const acceptedMessage = document.getElementById('acceptedMessage').value;
    const deniedMessage = document.getElementById('deniedMessage').value;
    
    // Get selected roles
    const restrictedRoles = Array.from(document.getElementById('restrictedRoles').selectedOptions).map(option => option.value);
    const requiredRoles = Array.from(document.getElementById('requiredRoles').selectedOptions).map(option => option.value);
    const buttonRoles = Array.from(document.getElementById('buttonRoles').selectedOptions).map(option => option.value);
    const acceptedRoles = Array.from(document.getElementById('acceptedRoles').selectedOptions).map(option => option.value);
    const deniedRoles = Array.from(document.getElementById('deniedRoles').selectedOptions).map(option => option.value);
    const pingRoles = Array.from(document.getElementById('pingRoles').selectedOptions).map(option => option.value);
    const acceptedRemovalRoles = Array.from(document.getElementById('acceptedRemovalRoles').selectedOptions).map(option => option.value);
    const deniedRemovalRoles = Array.from(document.getElementById('deniedRemovalRoles').selectedOptions).map(option => option.value);
    
    // Get questions
    const questions = Array.from(document.querySelectorAll('.question-input')).map(input => input.value);
    
    // Prepare data
    const data = {
        name: position,
        settings: {
            enabled: enabled,
            questions: questions,
            log_channel: logChannel,
            welcome_message: welcomeMessage,
            completion_message: completionMessage,
            accepted_message: acceptedMessage,
            denied_message: deniedMessage,
            restricted_roles: restrictedRoles,
            required_roles: requiredRoles,
            button_roles: buttonRoles,
            accepted_roles: acceptedRoles,
            denied_roles: deniedRoles,
            ping_roles: pingRoles,
            accepted_removal_roles: acceptedRemovalRoles,
            denied_removal_roles: deniedRemovalRoles
        }
    };
    
    // Send request
    fetch('/api/questions/position/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then(response => response.text())
    .then(message => {
        showToast('Success', message);
    })
    .catch(error => {
        showToast('Error', error.message);
    });
} 