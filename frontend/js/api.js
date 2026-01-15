// API Communication Module

import { triggerSessionRestart,authenticatedFetch } from './auth.js';

async function handleResponse(response) {
    if (response.status === 401 || response.status === 403 || response.status === 500) {
        const data = await response.json().catch(() => ({}));
        if (data.error === 'invalid_grant' || response.status === 401 || response.status === 403) {
            triggerSessionRestart();
            return null;
        }
    }
    return response;
}

export async function safeFetch(url, options = {}) {
    try {
        // Always include credentials for cookies
        options.credentials = 'include';
        
        const response = await fetch(url, options);
        const handledResponse = await handleResponse(response);
        if (!handledResponse) return null;
        return handledResponse;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
}

export async function fetchLatestEmails(emailId) {
    return await authenticatedFetch('/email/fetch_latest', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ email: emailId })
    });
}

export async function fetchEmailThread(emailId, threadId, tone) {
    return await authenticatedFetch('/email/draft', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ threadId, tone, email: emailId })
    });
}

export async function regenerateDraftAPI( userStyle, thread_id) {
    return await authenticatedFetch('/email/regenerate_draft', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ user_style: userStyle, thread_id: thread_id })
    });
}

export async function sendEmailAPI(emailId, threadId, draftBody, toEmail, draftOnly = false) {
    return await authenticatedFetch('/email/send', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ 
            email: emailId, 
            thread_id: threadId, 
            draft_body: draftBody, 
            draft_only: draftOnly, 
            toEmail: toEmail
        })
    });
}
