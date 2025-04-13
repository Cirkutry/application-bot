// Toast utility functions
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