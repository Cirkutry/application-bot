async function submitPanel(event) {
    event.preventDefault();
    
    // Check channel ID first
    const channelId = document.getElementById('channelId').value.trim();
    if (!channelId) {
        showErrorToast('Please enter a Channel ID');
        return;
    }

    // Check title and description
    const title = document.getElementById('embedTitle').value.trim();
    if (!title) {
        showErrorToast('Please enter a title');
        return;
    }

    const description = document.getElementById('embedDescription').value.trim();
    if (!description) {
        showErrorToast('Please enter a description');
        return;
    }
    
    // Get selected positions
    const selectedPositions = Array.from(document.querySelectorAll('input[name="positions"]:checked'))
        .map(checkbox => checkbox.value);
    
    if (selectedPositions.length === 0) {
        showErrorToast('Please select at least one position');
        return;
    }

    // Validate URLs
    const urlFields = ['embedUrl', 'embedAuthorUrl', 'embedAuthorIconUrl', 'embedThumbnailUrl', 'embedImageUrl', 'embedFooterIconUrl'];
    for (const fieldId of urlFields) {
        const input = document.getElementById(fieldId);
        if (input.value && !isValidUrl(input.value)) {
            input.classList.add('is-invalid');
            showErrorToast('Please enter a valid URL (https://example.com)');
            return;
        }
    }
    
    // Get form data
    const data = {
        channel_id: channelId,
        title: title,
        url: document.getElementById('embedUrl').value || null,
        description: description,
        color: document.getElementById('embedColor').value,
        author: {
            name: document.getElementById('embedAuthorName').value || null,
            url: document.getElementById('embedAuthorUrl').value || null,
            icon_url: document.getElementById('embedAuthorIconUrl').value || null
        },
        thumbnail: {
            url: document.getElementById('embedThumbnailUrl').value || null
        },
        image: {
            url: document.getElementById('embedImageUrl').value || null
        },
        footer: {
            text: document.getElementById('embedFooterText').value || null,
            icon_url: document.getElementById('embedFooterIconUrl').value || null
        },
        positions: selectedPositions
    };
    
    try {
        const response = await fetch('/api/panels/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            showSuccessToast('Panel created successfully');
            // Clear the form fields
            document.getElementById('panelForm').reset();
        } else {
            const responseText = await response.text();
            if (responseText.includes("'channel_id'")) {
                showErrorToast('Invalid channel ID, it must be a number');
            } else {
                showErrorToast(`Failed to create panel: ${responseText}`);
            }
        }
    } catch (error) {
        console.error('Error:', error);
        showErrorToast('An error occurred while creating the panel');
    }
}

// URL validation function
function isValidUrl(string) {
    try {
        new URL(string);
        return true;
    } catch (_) {
        return false;
    }
}

// Color picker functionality
document.addEventListener('DOMContentLoaded', function() {
    const colorInput = document.getElementById('embedColor');
    const colorPicker = document.getElementById('embedColorPicker');

    // Update color picker when hex input changes
    colorInput.addEventListener('input', function(e) {
        const value = e.target.value;
        if (/^#[0-9A-F]{6}$/i.test(value)) {
            colorPicker.value = value;
        }
    });

    // Update hex input when color picker changes
    colorPicker.addEventListener('input', function(e) {
        colorInput.value = e.target.value;
    });

    // Validate hex color on blur
    colorInput.addEventListener('blur', function(e) {
        const value = e.target.value;
        if (!/^#[0-9A-F]{6}$/i.test(value)) {
            e.target.value = '#5865F2';
            colorPicker.value = '#5865F2';
        }
    });
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    handleUrlParams();
    
    // Initialize Select2 for all select elements
    initializeSelect2('select');
});