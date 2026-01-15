// Authentication Module

export let isLoggedIn = false;
export let emailId = "";
export let draftTone = "Professional"; // Default tone

export function setAuthState(loggedIn, email) {
    isLoggedIn = loggedIn;
    emailId = email;
}

export function getAuthState() {
    return { isLoggedIn, emailId, draftTone };
}

export function triggerSessionRestart() {
    handleAuth();
    const sessionModal = new bootstrap.Modal(document.getElementById('sessionExpiredModal'));
    sessionModal.show();
}

export function restartAuthFlow() {
    window.location.href = "/login";
}

export async function handleAuth() {
    const authBtn = document.getElementById('auth-btn');
    
    if (!isLoggedIn) {
        window.location.href = "/login";
    } else {
        // Logout: call backend and clear local state
        try {
            await fetch('/auth/logout', {
                method: 'POST',
                credentials: 'include'
            });
        } catch (error) {
            console.error('Logout error:', error);
        }
        
        isLoggedIn = false;
        emailId = "";
        localStorage.removeItem('draftly_session');
        localStorage.removeItem('session_email');
        
       
        authBtn.innerText = "Login";
        authBtn.classList.replace('btn-danger', 'btn-primary');
        document.getElementById('email-list').innerHTML = "";
        window.location.href = "/login";
    }
}

export function updateAuthUI() {
    const authBtn = document.getElementById('auth-btn');
    if (isLoggedIn && emailId) {
        authBtn.innerText = "Logout";
        authBtn.classList.replace('btn-primary', 'btn-danger');
    }
}

export async function generateSessionToken(email) { // not used currently
    let sessionToken = localStorage.getItem('draftly_session');
    if (sessionToken) return sessionToken;
    const timestamp = Date.now();
    const randomData = Math.random().toString(36).substring(7);
    const rawString = `${timestamp}-${email}-${randomData}`;
    sessionToken = btoa(rawString);

    localStorage.setItem('draftly_session', sessionToken);
    localStorage.setItem('session_email', email);
    
    return sessionToken;
}

export async function authenticatedFetch(url, options = {}) {
    const token = localStorage.getItem('draftly_session');
    options.credentials = 'include';
    const headers = {
        ...options.headers,
        'X-Session-Token': token
    };

    const response = await fetch(url, { ...options, headers });
    if (response.status === 401) {
        triggerSessionRestart(); 
        return;
    }

    return response.json();
}