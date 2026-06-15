// Theme Management - Make functions globally available
window.initTheme = function() {
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeButton(theme);
}

window.toggleTheme = function() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeButton(newTheme);
    
    // Add a subtle animation effect
    document.body.style.transition = 'filter 0.3s ease';
    document.body.style.filter = 'brightness(0.98)';
    setTimeout(() => {
        document.body.style.filter = 'brightness(1)';
    }, 150);
}

function updateThemeButton(theme) {
    const themeButtons = document.querySelectorAll('.theme-toggle');
    themeButtons.forEach(btn => {
        const icon = btn.querySelector('.theme-toggle-icon');
        const text = btn.querySelector('.theme-toggle-text');
        if (icon) {
            if (theme === 'dark') {
                icon.innerHTML = '☀️';
                btn.title = 'Switch to Light Mode';
            } else {
                icon.innerHTML = '🌙';
                btn.title = 'Switch to Dark Mode';
            }
        }
    });
}

// Simple form handling
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme
    if (typeof initTheme === 'function') {
        initTheme();
    }

    const addStudentForm = document.getElementById('addStudentForm');
    const addCourseForm = document.getElementById('addCourseForm');

    if (addStudentForm) {
        addStudentForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Student form submitted');
        });
    }

    if (addCourseForm) {
        addCourseForm.addEventListener('submit', function(e) {
            e.preventDefault();
            console.log('Course form submitted');
        });
    }
});

function deleteCourse(courseCode) {
    if (confirm('Are you sure you want to delete this course?')) {
        fetch(`/delete-course/${courseCode}`, {
            method: 'POST',
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Reload the page to show updated list
                window.location.reload();
            } else {
                alert('Error deleting course: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error deleting course');
        });
    }
}

let editMode = false;

function toggleEditMode() {
    editMode = !editMode;
    const deleteButtons = document.querySelectorAll('.btn-delete');
    const editModeBtn = document.getElementById('editModeBtn');
    
    deleteButtons.forEach(button => {
        button.disabled = !editMode;
        button.classList.toggle('disabled');
    });
    
    editModeBtn.textContent = editMode ? 'Disable Edit Mode' : 'Enable Edit Mode';
    editModeBtn.classList.toggle('active');
}

// Initialize theme immediately when script loads
(function() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initTheme();
        });
    } else {
        initTheme();
    }
})();
