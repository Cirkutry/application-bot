// Panel management functions
async function submitPanel(event) {
    event.preventDefault();
    const panelName = document.getElementById('panelName').value.trim();
    const panelDescription = document.getElementById('panelDescription').value.trim();
    const panelColor = document.getElementById('panelColor').value;
    const panelEmoji = document.getElementById('panelEmoji').value;
    const panelRoles = Array.from(document.getElementById('panelRoles').selectedOptions).map(option => option.value);
    
    if (!panelName) {
        showErrorToast('Please enter a panel name');
        return;
    }

    try {
        const response = await fetch('/api/panels', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: panelName,
                description: panelDescription,
                color: panelColor,
                emoji: panelEmoji,
                roles: panelRoles
            })
        });

        if (response.ok) {
            showSuccessToast('Panel created successfully');
            document.getElementById('createPanelForm').reset();
            closeCreatePanelModal();
        } else {
            const responseText = await response.text();
            showErrorToast(`Failed to create panel: ${responseText}`);
        }
    } catch (error) {
        console.error('Error:', error);
        showErrorToast('An error occurred while creating the panel');
    }
}

async function deletePanel(panelId) {
    if (!confirm('Are you sure you want to delete this panel?')) {
        return;
    }

    try {
        const response = await fetch(`/api/panels/${panelId}`, {
            method: 'DELETE'
        });

        if (response.ok) {
            showSuccessToast('Panel deleted successfully');
            // Remove the panel from the UI
            const panelElement = document.getElementById(`panel-${panelId}`);
            if (panelElement) {
                panelElement.remove();
            }
        } else {
            const responseText = await response.text();
            showErrorToast(`Failed to delete panel: ${responseText}`);
        }
    } catch (error) {
        console.error('Error:', error);
        showErrorToast('An error occurred while deleting the panel');
    }
}

// Modal functions
function openCreatePanelModal() {
    document.getElementById('createPanelModal').style.display = 'block';
    document.getElementById('panelName').value = '';
    document.getElementById('panelDescription').value = '';
    document.getElementById('panelName').focus();
}

function closeCreatePanelModal() {
    document.getElementById('createPanelModal').style.display = 'none';
}

// Channel settings form submission
async function submitChannelSettings(event) {
    event.preventDefault();
    const channelId = document.getElementById('channelId').value.trim();
    const panelId = document.getElementById('panelId').value;
    
    if (!channelId) {
        showErrorToast('Please enter a channel ID');
        return;
    }

    try {
        const response = await fetch('/api/panels/channel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                panel_id: panelId,
                channel_id: channelId
            })
        });

        if (response.ok) {
            showSuccessToast('Channel settings updated successfully');
            document.getElementById('channelSettingsForm').reset();
        } else {
            const responseText = await response.text();
            showErrorToast(`Failed to update channel settings: ${responseText}`);
        }
    } catch (error) {
        console.error('Error:', error);
        showErrorToast('An error occurred while updating channel settings');
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    handleUrlParams();
    
    // Initialize Select2 for all select elements
    initializeSelect2('select');
    
    // Close modal when clicking outside
    window.onclick = function(event) {
        const modal = document.getElementById('createPanelModal');
        if (event.target == modal) {
            closeCreatePanelModal();
        }
    }
}); 