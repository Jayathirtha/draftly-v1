// Main Application Entry Point

import { handleAuth, setAuthState, updateAuthUI, restartAuthFlow } from './auth.js';
import { syncEmails, startAutoPolling, regenerateDraft } from './emailManager.js';
import { approveAndSend, draftEmail } from './draftActions.js';

// Expose functions to global scope for inline onclick handlers
window.handleAuth = handleAuth;
window.syncEmails = syncEmails;
window.approveAndSend = approveAndSend;
window.draftEmail = draftEmail;
window.regenerateDraft = regenerateDraft;
window.restartAuthFlow = restartAuthFlow;

// Initialize on page load - fetch user from server
async function initializeApp() {
    try {
        // Try to get authenticated user from server
        const response = await fetch('/auth/me', {
            method: 'GET',
            credentials: 'include' // Include cookies
        });
        
        if (response.ok) {
            const data = await response.json();
            const sessionToken = response.headers.get('session_token');
            if (sessionToken) {
                localStorage.setItem('draftly_session', sessionToken);
            }
            setAuthState(true, data.email);
            updateAuthUI();
            startAutoPolling();
            await syncEmails(); // Initial sync
        } else {
            // Not authenticated, redirect to login
            if (window.location.pathname === '/home') {
                window.location.href = '/login';
            }
        }
    } catch (error) {
        console.error('Auth check failed:', error);
        if (window.location.pathname === '/home') {
            window.location.href = '/login';
        }
    }
}

// Event Listeners
window.addEventListener('DOMContentLoaded', () => {
    updateAuthUI();
    initializeApp();
});

