async function submitPosition(event) {
    event.preventDefault();
    const positionName = document.getElementById('positionName').value.trim();
    const copyFrom = document.getElementById('copyFrom').value;
    
    if (!positionName) {
        showErrorToast('Please enter a position name');
        return;
    }

    try {
        const response = await fetch('/api/questions/position/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: positionName,
                copy_from: copyFrom
            })
        });

        const responseText = await response.text();
        
        if (response.ok) {
            document.getElementById('addPositionForm').reset();
            closeAddPositionModal();

            sessionStorage.setItem('toastMessage', 'Position added successfully');
            sessionStorage.setItem('toastType', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showErrorToast(`Failed to add position: ${responseText}`);
        }
    } catch (error) {
        console.error('Error:', error);
        showErrorToast('An error occurred while adding the position');
    }
}

async function submitEditPosition(event) {
    event.preventDefault();
    const positionName = document.getElementById('editPositionName').value;
    const settings = {
        enabled: document.getElementById('positionEnabled').checked,
        auto_thread: document.getElementById('autoThread').checked,
        log_channel: document.getElementById('logChannel').value,
        welcome_message: document.getElementById('welcomeMessage').value,
        completion_message: document.getElementById('completionMessage').value,
        accepted_message: document.getElementById('acceptedMessage').value,
        denied_message: document.getElementById('deniedMessage').value,
        restricted_roles: Array.from(document.getElementById('restrictedRoles').selectedOptions).map(option => option.value),
        required_roles: Array.from(document.getElementById('requiredRoles').selectedOptions).map(option => option.value),
        button_roles: Array.from(document.getElementById('buttonRoles').selectedOptions).map(option => option.value),
        accepted_roles: Array.from(document.getElementById('acceptedRoles').selectedOptions).map(option => option.value),
        denied_roles: Array.from(document.getElementById('deniedRoles').selectedOptions).map(option => option.value),
        ping_roles: Array.from(document.getElementById('pingRoles').selectedOptions).map(option => option.value),
        accepted_removal_roles: Array.from(document.getElementById('acceptedRemovalRoles').selectedOptions).map(option => option.value),
        denied_removal_roles: Array.from(document.getElementById('deniedRemovalRoles').selectedOptions).map(option => option.value),
        questions: Array.from(document.querySelectorAll('.question-item'))
            .map(item => item.querySelector('input').value.trim())
            .filter(question => question !== '') // Filter out empty questions
    };

    try {
        const response = await fetch('/api/questions/position/update', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: positionName,
                settings: settings
            })
        });

        if (response.ok) {

            sessionStorage.setItem('toastMessage', 'Position updated successfully');
            sessionStorage.setItem('toastType', 'success');
            window.location.href = '/positions';
        } else {
            const responseText = await response.text();
            showErrorToast(`Failed to update position: ${responseText}`);
        }
    } catch (error) {
        console.error('Error:', error);
        showErrorToast('An error occurred while updating the position');
    }
}

async function duplicatePosition(position) {
    const newName = `${position} - Copy`;
    
    try {
        const response = await fetch('/api/questions/position/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: newName,
                copy_from: position
            })
        });

        const responseText = await response.text();
        
        if (response.ok) {
            // Store the success message in sessionStorage
            sessionStorage.setItem('toastMessage', 'Position duplicated successfully');
            sessionStorage.setItem('toastType', 'success');
            setTimeout(() => location.reload(), 1000);
        } else {
            showErrorToast(`Failed to duplicate position: ${responseText}`);
        }
    } catch (error) {
        console.error('Error:', error);
        showErrorToast('An error occurred while duplicating the position');
    }
}

async function deletePosition(position) {
    try {
        const response = await fetch('/api/questions/position/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                position: position
            })
        });

        const responseText = await response.text();
        
        if (response.ok) {
            // Store the success message in sessionStorage
            sessionStorage.setItem('toastMessage', 'Position deleted successfully');
            sessionStorage.setItem('toastType', 'failure');
            setTimeout(() => location.reload(), 1000);
        } else {
            showErrorToast(`Failed to delete position: ${responseText}`);
        }
    } catch (error) {
        console.error('Error:', error);
        showErrorToast('An error occurred while deleting the position');
    }
}

// Modal functions
function openAddPositionModal() {
    const modal = document.getElementById('addPositionModal');
    if (modal) {
        modal.style.display = 'block';
        document.getElementById('positionName').value = '';
        document.getElementById('positionName').focus();
    }
}

function closeAddPositionModal() {
    const modal = document.getElementById('addPositionModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

function openEditPositionModal(button) {
    const position = button.dataset.position;
    const data = JSON.parse(button.dataset.settings);
    
    if (!data) return;
    
    // Show the modal first
    document.getElementById('editPositionModal').style.display = 'block';
    document.getElementById('editPositionName').value = position;
    
    // Set form values
    document.getElementById('positionEnabled').checked = data.enabled;
    document.getElementById('autoThread').checked = data.auto_thread;
    document.getElementById('logChannel').value = data.log_channel;
    document.getElementById('welcomeMessage').value = data.welcome_message;
    document.getElementById('acceptedMessage').value = data.accepted_message;
    document.getElementById('deniedMessage').value = data.denied_message;
    document.getElementById('completionMessage').value = data.completion_message;
    
    // Set role selections
    const roleSelects = [
        'restrictedRoles',
        'requiredRoles',
        'acceptedRoles',
        'deniedRoles',
        'pingRoles',
        'acceptedRemovalRoles',
        'deniedRemovalRoles'
    ];
    
    // Initialize Select2 for each select element
    roleSelects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select) {
            // Destroy any existing Select2 instance
            if ($(select).hasClass('select2-hidden-accessible')) {
                $(select).select2('destroy');
            }
            
            // Initialize Select2 with modal-specific configuration
            $(select).select2({
                theme: 'bootstrap-5',
                width: '100%',
                placeholder: 'Select options...',
                allowClear: true,
                closeOnSelect: false,
                dropdownParent: $('#editPositionModal')
            });
            
            // Set the values
            $(select).val(data[selectId.replace('Roles', '_roles')] || []).trigger('change');
        }
    });
    
    // Populate questions
    populateQuestionsList(data.questions);
}

function closeEditPositionModal() {
    // Destroy all Select2 instances before closing
    const roleSelects = [
        'restrictedRoles',
        'requiredRoles',
        'acceptedRoles',
        'deniedRoles',
        'pingRoles',
        'acceptedRemovalRoles',
        'deniedRemovalRoles'
    ];
    
    roleSelects.forEach(selectId => {
        const select = document.getElementById(selectId);
        if (select && $(select).hasClass('select2-hidden-accessible')) {
            $(select).select2('destroy');
        }
    });
    
    document.getElementById('editPositionModal').style.display = 'none';
}

function openDeleteConfirmationModal(position) {
    const modal = document.getElementById('deleteConfirmationModal');
    if (modal) {
        modal.style.display = 'block';
        // Store the position to be deleted in the modal's dataset
        modal.dataset.position = position;
        // Update the modal message to show the position name
        const modalMessage = document.querySelector('#deleteConfirmationModal .modal-body p');
        modalMessage.innerHTML = `<i class="fa-solid fa-triangle-exclamation me-2"></i>Are you sure you want to delete the position: "${position}"?`;
    }
}

function closeDeleteConfirmationModal() {
    const modal = document.getElementById('deleteConfirmationModal');
    if (modal) {
        modal.style.display = 'none';
        // Clear the stored position
        delete modal.dataset.position;
        // Reset the modal message
        const modalMessage = document.querySelector('#deleteConfirmationModal .modal-body p');
        modalMessage.innerHTML = '<i class="fa-solid fa-triangle-exclamation me-2"></i>Are you sure you want to delete this position?';
    }
}

function openDeleteQuestionModal(questionElement) {
    const modal = document.getElementById('deleteQuestionModal');
    if (modal) {
        modal.style.display = 'block';
        // Store the question element ID in the modal's dataset
        modal.dataset.questionId = questionElement.id;
        // Update the modal message to show the question content
        const questionText = questionElement.querySelector('.question-input').value;
        const modalMessage = document.querySelector('#deleteQuestionModal .modal-body p');
        modalMessage.textContent = `Are you sure you want to delete this question: "${questionText || 'Unnamed Question'}"?`;
    }
}

function closeDeleteQuestionModal() {
    const modal = document.getElementById('deleteQuestionModal');
    if (modal) {
        modal.style.display = 'none';
        // Clear the stored question ID
        delete modal.dataset.questionId;
        // Reset the modal message
        const modalMessage = document.querySelector('#deleteQuestionModal .modal-body p');
        modalMessage.textContent = 'Are you sure you want to delete this question?';
    }
}

// Questions management
function populateQuestionsList(questions) {
    const container = document.getElementById('questionsList');
    container.innerHTML = '';
    
    questions.forEach((question, index) => {
        const questionElement = document.createElement('div');
        questionElement.className = 'question-item';
        questionElement.id = 'question_' + Date.now() + '_' + index; // Add a unique ID
        questionElement.innerHTML = `
            <button type="button" class="btn btn-secondary btn-icon drag-handle" style="cursor: move;">
                <i class="fa-solid fa-arrows-up-down-left-right"></i>
            </button>
            <input type="text" class="form-control question-input" value="${question}">
            <button type="button" class="btn btn-danger btn-icon remove-question">
                <i class="fa-solid fa-xmark"></i>
            </button>
        `;
        container.appendChild(questionElement);
    });
}

function addQuestion() {
    const container = document.getElementById('questionsList');
    const questionElement = document.createElement('div');
    questionElement.className = 'question-item';
    questionElement.id = 'question_' + Date.now() + '_' + container.children.length; // Add a unique ID
    questionElement.innerHTML = `
        <button type="button" class="btn btn-secondary btn-icon drag-handle" style="cursor: move;">
            <i class="fa-solid fa-arrows-up-down-left-right"></i>
        </button>
        <input type="text" class="form-control question-input">
        <button type="button" class="btn btn-danger btn-icon remove-question">
            <i class="fa-solid fa-xmark"></i>
        </button>
    `;
    container.appendChild(questionElement);
}

function updateQuestionOrder() {
    const questions = Array.from(document.querySelectorAll('.question-input')).map(input => input.value);
    // The order is already maintained in the DOM, so we just need to collect the values
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    handleUrlParams();    
    // Check for stored toast message
    const toastMessage = sessionStorage.getItem('toastMessage');
    const toastType = sessionStorage.getItem('toastType');
    if (toastMessage) {
        if (toastType === 'success') {
            showSuccessToast(toastMessage);
        } else {
            showErrorToast(toastMessage);
        }
        // Clear the stored message
        sessionStorage.removeItem('toastMessage');
        sessionStorage.removeItem('toastType');
    }
    
    // Close modals when clicking outside
    window.onclick = function(event) {
        const addModal = document.getElementById('addPositionModal');
        const editModal = document.getElementById('editPositionModal');
        const deleteModal = document.getElementById('deleteConfirmationModal');
        const deleteQuestionModal = document.getElementById('deleteQuestionModal');
        
        if (event.target == addModal) {
            closeAddPositionModal();
        }
        if (event.target == editModal) {
            closeEditPositionModal();
        }
        if (event.target == deleteModal) {
            closeDeleteConfirmationModal();
        }
        if (event.target == deleteQuestionModal) {
            closeDeleteQuestionModal();
        }
    }

    // Initialize modals
    const addPositionModal = document.getElementById('addPositionModal');
    if (addPositionModal) {
        addPositionModal.style.display = 'none';
    }

    const deleteConfirmationModal = document.getElementById('deleteConfirmationModal');
    if (deleteConfirmationModal) {
        deleteConfirmationModal.style.display = 'none';
    }

    const deleteQuestionModal = document.getElementById('deleteQuestionModal');
    if (deleteQuestionModal) {
        deleteQuestionModal.style.display = 'none';
    }

    // Add Position button click handler
    const addPositionBtn = document.getElementById('addPositionBtn');
    if (addPositionBtn) {
        addPositionBtn.addEventListener('click', function() {
            console.log('Add Position button clicked');
            openAddPositionModal();
        });
    }

    // Add Question button click handler
    const addQuestionBtn = document.getElementById('addQuestionBtn');
    if (addQuestionBtn) {
        addQuestionBtn.addEventListener('click', function() {
            console.log('Add Question button clicked');
            addQuestion();
        });
    }

    // Close Add Position Modal button click handler
    const closeAddPositionModalBtn = document.getElementById('closeAddPositionModal');
    if (closeAddPositionModalBtn) {
        closeAddPositionModalBtn.addEventListener('click', function() {
            console.log('Close modal button clicked');
            closeAddPositionModal();
        });
    }

    // Cancel Add Position button click handler
    const cancelAddPositionBtn = document.getElementById('cancelAddPosition');
    if (cancelAddPositionBtn) {
        cancelAddPositionBtn.addEventListener('click', function() {
            console.log('Cancel button clicked');
            closeAddPositionModal();
        });
    }

    // Add Position Form submit handler
    const addPositionForm = document.getElementById('addPositionForm');
    if (addPositionForm) {
        addPositionForm.addEventListener('submit', function(event) {
            console.log('Form submitted');
            submitPosition(event);
        });
    }

    // Delete button click handlers
    document.querySelectorAll('.delete-btn').forEach(button => {
        button.addEventListener('click', function() {
            const position = this.dataset.position;
            console.log('Delete button clicked for position:', position);
            openDeleteConfirmationModal(position);
        });
    });

    // Close Delete Confirmation Modal button click handler
    const closeDeleteConfirmationModalBtn = document.getElementById('closeDeleteConfirmationModal');
    if (closeDeleteConfirmationModalBtn) {
        closeDeleteConfirmationModalBtn.addEventListener('click', function() {
            console.log('Close delete confirmation modal button clicked');
            closeDeleteConfirmationModal();
        });
    }

    // Cancel Delete button click handler
    const cancelDeleteBtn = document.getElementById('cancelDelete');
    if (cancelDeleteBtn) {
        cancelDeleteBtn.addEventListener('click', function() {
            console.log('Cancel delete button clicked');
            closeDeleteConfirmationModal();
        });
    }

    // Confirm Delete button click handler
    const confirmDeleteBtn = document.getElementById('confirmDelete');
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', async function() {
            const modal = document.getElementById('deleteConfirmationModal');
            const position = modal.dataset.position;
            console.log('Confirm delete button clicked for position:', position);
            closeDeleteConfirmationModal();
            await deletePosition(position);
        });
    }

    // Duplicate button click handlers
    document.querySelectorAll('.duplicate-btn').forEach(button => {
        button.addEventListener('click', function() {
            const position = this.dataset.position;
            console.log('Duplicate button clicked for position:', position);
            duplicatePosition(position);
        });
    });

    // Add event delegation for question removal and initialize Sortable
    const questionsList = document.getElementById('questionsList');
    if (questionsList) {
        // Initialize Sortable
        new Sortable(questionsList, {
            animation: 150,
            ghostClass: 'sortable-ghost',
            handle: '.drag-handle',
            onEnd: function() {
                // Update question order in hidden input
                updateQuestionOrder();
            }
        });

        // Ensure question items have unique IDs
        const questionItems = document.querySelectorAll('.question-item');
        questionItems.forEach((item, index) => {
            if (!item.id) {
                item.id = 'question_' + Date.now() + '_' + index;
            }
        });

        // Add event delegation for question removal
        questionsList.addEventListener('click', function(event) {
            if (event.target.closest('.remove-question')) {
                // Use the custom deleteQuestionModal instead of browser confirm dialog
                const questionItem = event.target.closest('.question-item');
                openDeleteQuestionModal(questionItem);
            }
        });
    }

    // Initialize the question delete confirmation modal buttons
    const closeDeleteQuestionModalBtn = document.getElementById('closeDeleteQuestionModal');
    if (closeDeleteQuestionModalBtn) {
        closeDeleteQuestionModalBtn.addEventListener('click', function() {
            console.log('Close question delete modal button clicked');
            closeDeleteQuestionModal();
        });
    }

    const cancelDeleteQuestionBtn = document.getElementById('cancelDeleteQuestion');
    if (cancelDeleteQuestionBtn) {
        cancelDeleteQuestionBtn.addEventListener('click', function() {
            console.log('Cancel question delete button clicked');
            closeDeleteQuestionModal();
        });
    }

    const confirmDeleteQuestionBtn = document.getElementById('confirmDeleteQuestion');
    if (confirmDeleteQuestionBtn) {
        confirmDeleteQuestionBtn.addEventListener('click', function() {
            const modal = document.getElementById('deleteQuestionModal');
            const questionId = modal.dataset.questionId;
            console.log('Confirm question delete button clicked for question ID:', questionId);
            
            // Find and remove the question element with the matching ID
            const questionElement = document.getElementById(questionId);
            if (questionElement) {
                questionElement.remove();
                console.log('Question removed successfully');
            }
            
            closeDeleteQuestionModal();
        });
    }
});