function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast bg-${type} text-white`;
    toast.innerHTML = `
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    const toastContainer = document.querySelector('.toast-container');
    if (!toastContainer) {
        const container = document.createElement('div');
        container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(container);
    }
    
    document.querySelector('.toast-container').appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    // Remove toast after it's hidden
    toast.addEventListener('hidden.bs.toast', function() {
        toast.remove();
    });
}

function showErrorToast(message) {
    showToast(message, 'danger');
}

function showSuccessToast(message) {
    showToast(message, 'success');
}

// URL parameter handling
function handleUrlParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const status = urlParams.get('status');
    const message = urlParams.get('message');

    if (status && message) {
        showToast(decodeURIComponent(message), status);
        window.history.replaceState({}, document.title, window.location.pathname);
    }
}

// Initialize Select2
function initializeSelect2(selector, options = {}) {
    // Ensure jQuery is loaded
    if (typeof $ === 'undefined') {
        console.error('jQuery is not loaded');
        return;
    }

    // Ensure Select2 is loaded
    if (typeof $.fn.select2 === 'undefined') {
        console.error('Select2 is not loaded');
        return;
    }

    // Destroy any existing instance
    if ($(selector).hasClass('select2-hidden-accessible')) {
        $(selector).select2('destroy');
    }

    // Initialize with default options
    $(selector).select2({
        theme: 'bootstrap-5',
        width: '100%',
        placeholder: 'Select options...',
        allowClear: true,
        closeOnSelect: false,
        ...options
    });
}

/**
 * Updates the status of an application and handles the UI feedback
 * @param {string} applicationId - The ID of the application to update
 * @param {string} status - The new status to set
 */
function updateStatus(applicationId, status) {
    if (!confirm(`Are you sure you want to ${status} this application?`)) {
        return;
    }

    fetch(`/api/applications/${applicationId}/status`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status })
    })
    .then(response => response.json())
    .then(result => {
        if (result.success) {
            showToast(`Application ${status}d successfully`, 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(result.error || 'Failed to update application status', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Failed to update application status', 'danger');
    });
}

/**
 * Updates the viewer roles configuration
 * @param {string[]} selectedRoles - Array of selected role IDs
 * @returns {Promise} Promise that resolves when the update is complete
 */
function saveViewerRoles() {
    const selectedRoles = $('#viewerRoles').val() || [];
    
    return fetch('/api/viewer-roles/update', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ roles: selectedRoles })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showToast('Viewer roles updated successfully', 'success');
        } else {
            showToast(data.error || 'Failed to update viewer roles', 'danger');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('Failed to update viewer roles', 'danger');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.querySelector('.hamburger-menu');
    const sidebar = document.querySelector('.sidebar');
    
    if (hamburger && sidebar) {
        hamburger.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
    }
});