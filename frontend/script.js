const API_BASE = 'http://localhost:5000/api';  // Keep this if running backend on port 5000

// DOM Elements
let currentStudentId = null;
let gradeChart = null;

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    loadDashboard();
    loadStudents();
    loadCourses();
    loadGrades();
});

// Navigation
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    // Remove active class from all nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected section and activate nav button
    document.getElementById(sectionName).classList.add('active');
    event.target.classList.add('active');
    
    // Refresh section data
    switch(sectionName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'students':
            loadStudents();
            break;
        case 'courses':
            loadCourses();
            break;
        case 'grades':
            loadGrades();
            break;
    }
}

// Dashboard Functions
async function loadDashboard() {
    try {
        const response = await fetch(`${API_BASE}/dashboard/stats`);
        const data = await response.json();
        
        if (data.success) {
            // Update stats cards
            document.getElementById('totalStudents').textContent = data.data.total_students;
            document.getElementById('totalCourses').textContent = data.data.total_courses;
            document.getElementById('totalGrades').textContent = data.data.total_grades;
            
            // Update grade chart
            updateGradeChart(data.data.grade_distribution);
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function updateGradeChart(gradeDistribution) {
    const ctx = document.getElementById('gradeChart').getContext('2d');
    
    if (gradeChart) {
        gradeChart.destroy();
    }
    
    const labels = gradeDistribution.map(item => item._id);
    const data = gradeDistribution.map(item => item.count);
    const backgroundColors = [
        '#10B981', '#34D399', '#3B82F6', '#60A5FA', 
        '#F59E0B', '#FBBF24', '#EF4444', '#F87171', '#6B7280'
    ];
    
    gradeChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: backgroundColors,
                borderWidth: 2,
                borderColor: '#1F2937'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: 'white',
                        font: {
                            size: 12
                        }
                    }
                }
            }
        }
    });
}

// Student Functions
async function loadStudents() {
    try {
        const response = await fetch(`${API_BASE}/students`);
        const data = await response.json();
        
        if (data.success) {
            const table = document.getElementById('studentsTable');
            table.innerHTML = '';
            
            data.data.forEach(student => {
                const row = document.createElement('tr');
                row.className = 'border-b border-gray-700 hover:bg-gray-800 transition-colors';
                row.innerHTML = `
                    <td class="py-3 px-4 font-mono">${student.roll_no}</td>
                    <td class="py-3 px-4">${student.name}</td>
                    <td class="py-3 px-4">${student.email}</td>
                    <td class="py-3 px-4">${student.department}</td>
                    <td class="py-3 px-4">Semester ${student.semester}</td>
                    <td class="py-3 px-4">
                        <div class="flex space-x-2">
                            <button onclick="viewStudentGrades('${student._id}')" class="text-blue-400 hover:text-blue-300">
                                <i class="fas fa-chart-bar"></i>
                            </button>
                            <button onclick="editStudent('${student._id}')" class="text-green-400 hover:text-green-300">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button onclick="deleteStudent('${student._id}')" class="text-red-400 hover:text-red-300">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                `;
                table.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading students:', error);
    }
}

function openStudentModal(student = null) {
    const modal = document.getElementById('studentModal');
    const title = document.getElementById('studentModalTitle');
    const form = document.getElementById('studentForm');
    
    if (student) {
        // Edit student
        currentStudentId = student._id;
        title.textContent = 'Edit Student';
        document.getElementById('studentName').value = student.name;
        document.getElementById('studentEmail').value = student.email;
        document.getElementById('studentId').value = student.roll_no;
        document.getElementById('studentDepartment').value = student.department;
        document.getElementById('studentSemester').value = student.semester;
    } else {
        // Add student
        currentStudentId = null;
        title.textContent = 'Add Student';
        form.reset();
    }
    
    modal.style.display = 'flex';
}

function closeStudentModal() {
    const modal = document.getElementById('studentModal');
    modal.style.display = 'none';
}

document.getElementById('studentForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const data = {
        name: document.getElementById('studentName').value,
        email: document.getElementById('studentEmail').value,
        roll_no: document.getElementById('studentId').value,
        department: document.getElementById('studentDepartment').value,
        semester: document.getElementById('studentSemester').value
    };
    
    try {
        let response;
        if (currentStudentId) {
            // Update student
            response = await fetch(`${API_BASE}/students/${currentStudentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        } else {
            // Create student
            response = await fetch(`${API_BASE}/students`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            closeStudentModal();
            loadStudents();
            showAlert('Student saved successfully!', 'success');
        } else {
            showAlert(result.error, 'error');
        }
    } catch (error) {
        console.error('Error saving student:', error);
        showAlert('An error occurred while saving the student.', 'error');
    }
});

// Course Functions
async function loadCourses() {
    try {
        const response = await fetch(`${API_BASE}/courses`);
        const data = await response.json();
        
        if (data.success) {
            const grid = document.getElementById('coursesGrid');
            grid.innerHTML = '';
            
            data.data.forEach(course => {
                const card = document.createElement('div');
                card.className = 'glass-card p-4';
                card.innerHTML = `
                    <h3 class="text-xl font-semibold">${course.course_name}</h3>
                    <p class="text-gray-400">${course.course_code} - ${course.credits} Credits</p>
                    <div class="mt-4 flex space-x-2">
                        <button onclick="editCourse('${course._id}')" class="btn-secondary flex-1">
                            <i class="fas fa-edit mr-2"></i>Edit Course
                        </button>
                        <button onclick="deleteCourse('${course._id}')" class="btn-danger flex-1">
                            <i class="fas fa-trash mr-2"></i>Delete Course
                        </button>
                    </div>
                `;
                grid.appendChild(card);
            });
        }
    } catch (error) {
        console.error('Error loading courses:', error);
    }
}

function openCourseModal(course = null) {
    const modal = document.getElementById('courseModal');
    const form = document.getElementById('courseForm');
    
    if (course) {
        // Edit course
        currentCourseId = course._id;
        document.getElementById('courseCode').value = course.course_code;
        document.getElementById('courseName').value = course.course_name;
        document.getElementById('courseCredits').value = course.credits;
        document.getElementById('courseDepartment').value = course.department;
        document.getElementById('courseInstructor').value = course.instructor;
    } else {
        // Add course
        currentCourseId = null;
        form.reset();
    }
    
    modal.style.display = 'flex';
}

function closeCourseModal() {
    const modal = document.getElementById('courseModal');
    modal.style.display = 'none';
}

document.getElementById('courseForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const data = {
        course_code: document.getElementById('courseCode').value,
        course_name: document.getElementById('courseName').value,
        credits: document.getElementById('courseCredits').value,
        department: document.getElementById('courseDepartment').value,
        instructor: document.getElementById('courseInstructor').value
    };
    
    try {
        let response;
        if (currentCourseId) {
            // Update course
            response = await fetch(`${API_BASE}/courses/${currentCourseId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        } else {
            // Create course
            response = await fetch(`${API_BASE}/courses`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            closeCourseModal();
            loadCourses();
            showAlert('Course saved successfully!', 'success');
        } else {
            showAlert(result.error, 'error');
        }
    } catch (error) {
        console.error('Error saving course:', error);
        showAlert('An error occurred while saving the course.', 'error');
    }
});

// Grade Functions
async function loadGrades() {
    try {
        const response = await fetch(`${API_BASE}/grades`);
        const data = await response.json();
        
        if (data.success) {
            const table = document.getElementById('gradesTable');
            table.innerHTML = '';
            
            data.data.forEach(grade => {
                const row = document.createElement('tr');
                row.className = 'border-b border-gray-700 hover:bg-gray-800 transition-colors';
                row.innerHTML = `
                    <td class="py-3 px-4">${grade.student_name}</td>
                    <td class="py-3 px-4">${grade.course_name}</td>
                    <td class="py-3 px-4">${grade.grade}</td>
                    <td class="py-3 px-4">Semester ${grade.semester}</td>
                    <td class="py-3 px-4">
                        <div class="flex space-x-2">
                            <button onclick="editGrade('${grade._id}')" class="text-green-400 hover:text-green-300">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button onclick="deleteGrade('${grade._id}')" class="text-red-400 hover:text-red-300">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                `;
                table.appendChild(row);
            });
        }
    } catch (error) {
        console.error('Error loading grades:', error);
    }
}

function openGradeModal(grade = null) {
    const modal = document.getElementById('gradeModal');
    const form = document.getElementById('gradeForm');
    
    if (grade) {
        // Edit grade
        currentGradeId = grade._id;
        document.getElementById('gradeStudent').value = grade.roll_no;
        document.getElementById('gradeCourse').value = grade.course_code;
        document.getElementById('gradeValue').value = grade.grade;
        document.getElementById('gradeSemester').value = grade.semester;
    } else {
        // Add grade
        currentGradeId = null;
        form.reset();
    }
    
    modal.style.display = 'flex';
}

function closeGradeModal() {
    const modal = document.getElementById('gradeModal');
    modal.style.display = 'none';
}

document.getElementById('gradeForm').addEventListener('submit', async function(event) {
    event.preventDefault();
    
    const data = {
        roll_no: document.getElementById('gradeStudent').value,
        course_code: document.getElementById('gradeCourse').value,
        grade: document.getElementById('gradeValue').value,
        semester: document.getElementById('gradeSemester').value
    };
    
    try {
        let response;
        if (currentGradeId) {
            // Update grade
            response = await fetch(`${API_BASE}/grades/${currentGradeId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        } else {
            // Create grade
            response = await fetch(`${API_BASE}/grades`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });
        }
        
        const result = await response.json();
        
        if (result.success) {
            closeGradeModal();
            loadGrades();
            showAlert('Grade saved successfully!', 'success');
        } else {
            showAlert(result.error, 'error');
        }
    } catch (error) {
        console.error('Error saving grade:', error);
        showAlert('An error occurred while saving the grade.', 'error');
    }
});

function showAlert(message, type) {
    const alertBox = document.createElement('div');
    alertBox.className = `fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg transition-all duration-300`;
    alertBox.classList.add(type === 'success' ? 'bg-green-500' : 'bg-red-500');
    alertBox.innerHTML = `
        <div class="flex items-center">
            <i class="fas fa-${type === 'success' ? 'check' : 'times'} mr-3"></i>
            <span class="text-white font-semibold">${message}</span>
        </div>
    `;
    
    document.body.appendChild(alertBox);
    
    setTimeout(() => {
        alertBox.classList.add('opacity-0');
        setTimeout(() => {
            document.body.removeChild(alertBox);
        }, 300);
    }, 3000);
}