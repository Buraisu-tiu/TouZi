// Check session expiry and auto logout
const SESSION_TIMEOUT = 30 * 60 * 1000; // 30 minutes in milliseconds
const LAST_ACTIVITY_KEY = 'lastActivity';

function checkSession() {
    const lastActivity = localStorage.getItem(LAST_ACTIVITY_KEY);
    const currentTime = new Date().getTime();
    
    if (lastActivity && (currentTime - lastActivity) > SESSION_TIMEOUT) {
        logout();
    } else {
        localStorage.setItem(LAST_ACTIVITY_KEY, currentTime);
    }
}

function logout() {
    localStorage.removeItem(LAST_ACTIVITY_KEY);
    window.location.href = '/auth/logout';
}

// Check session on page load
document.addEventListener('DOMContentLoaded', checkSession);
// Update last activity on user interaction
document.addEventListener('click', () => {
    localStorage.setItem(LAST_ACTIVITY_KEY, new Date().getTime());
});
