window.showNotification = function(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `fixed top-4 right-4 z-50 px-6 py-4 rounded-lg shadow-lg transform transition-all duration-300 ${getNotificationClass(type)}`;
    notification.innerHTML = `
        <div class="flex items-center">
            <i class="${getNotificationIcon(type)} mr-3"></i>
            <span>${message}</span>
        </div>
    `;
    
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
};

function getNotificationClass(type) {
    const classes = {
        'info': 'bg-blue-50 text-blue-800 border border-blue-200',
        'success': 'bg-green-50 text-green-800 border border-green-200',
        'warning': 'bg-yellow-50 text-yellow-800 border border-yellow-200',
        'error': 'bg-red-50 text-red-800 border border-red-200'
    };
    return classes[type] || classes.info;
}

function getNotificationIcon(type) {
    const icons = {
        'info': 'fas fa-info-circle',
        'success': 'fas fa-check-circle',
        'warning': 'fas fa-exclamation-triangle',
        'error': 'fas fa-times-circle'
    };
    return icons[type] || icons.info;
}

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация всех интерактивных элементов
    
    // Подсветка текущей страницы в навигации
    highlightCurrentPage();
    
    // Обработка кнопок открытия проектов
    initializeProjectButtons();
    
    // Обработка кнопок скачивания
    initializeDownloadButtons();
    
    // Обработка примеров кода
    initializeCodeExamples();
    
    // Обработка форм
    initializeForms();
});

function highlightCurrentPage() {
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

function initializeProjectButtons() {
    document.querySelectorAll('.open-project-btn').forEach(button => {
        button.addEventListener('click', function() {
            const projectName = this.getAttribute('data-project') || this.closest('.card').querySelector('h3').textContent;
            showNotification(`Открываем проект: ${projectName}`, 'info');
        });
    });
}

function initializeDownloadButtons() {
    document.querySelectorAll('.download-btn').forEach(button => {
        button.addEventListener('click', function() {
            const fileName = this.getAttribute('data-filename') || 'generated_code';
            showNotification(`Файл ${fileName} скачан`, 'success');
        });
    });
}

function initializeCodeExamples() {
    document.querySelectorAll('.code-example').forEach(example => {
        example.addEventListener('click', function() {
            const code = this.textContent;
            navigator.clipboard.writeText(code).then(() => {
                showNotification('Код скопирован в буфер обмена', 'success');
            });
        });
    });
}

function initializeForms() {
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitButton = this.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalText = submitButton.innerHTML;
                submitButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Обработка...';
                submitButton.disabled = true;
                
                setTimeout(() => {
                    submitButton.innerHTML = originalText;
                    submitButton.disabled = false;
                }, 2000);
            }
        });
    });
}

window.ajaxRequest = async function(url, method = 'GET', data = null, headers = {}) {
    try {
        const options = {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                ...headers
            },
            credentials: 'include'
        };
        
        if (data) {
            options.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, options);
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `Ошибка HTTP: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Ошибка при выполнении запроса:', error);
        showNotification(`Ошибка: ${error.message}`, 'error');
        throw error;
    }
};

// Функция для проверки авторизации
window.checkAuth = async function() {
    try {
        const response = await fetch('/api/users/me', {
            credentials: 'include'
        });
        return response.ok;
    } catch (error) {
        return false;
    }
};

// Функция для получения текущего пользователя
window.getCurrentUser = async function() {
    try {
        const response = await fetch('/api/users/me', {
            credentials: 'include'
        });
        if (response.ok) {
            return await response.json();
        }
        return null;
    } catch (error) {
        return null;
    }
};

// Функция для выхода
window.logout = async function() {
    try {
        const response = await fetch('/api/logout', {
            method: 'POST',
            credentials: 'include'
        });
        
        if (response.ok) {
            showNotification('Вы успешно вышли из системы', 'success');
            setTimeout(() => {
                window.location.href = '/';
            }, 1000);
        }
    } catch (error) {
        console.error('Ошибка при выходе:', error);
        showNotification('Ошибка при выходе из системы', 'error');
    }
};

document.addEventListener('click', function(e) {
    if (e.target.closest('[data-logout]')) {
        e.preventDefault();
        window.logout();
    }
    
    if (e.target.closest('[data-copy]')) {
        e.preventDefault();
        const text = e.target.closest('[data-copy]').getAttribute('data-copy-text') ||
                    e.target.closest('[data-copy]').textContent;
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Текст скопирован в буфер обмена', 'success');
        });
    }
});