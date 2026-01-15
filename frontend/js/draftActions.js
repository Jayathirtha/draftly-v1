// Draft Actions Module (Send & Save)

import { sendEmailAPI } from './api.js';
import { getAuthState } from './auth.js';
import { syncEmails } from './emailManager.js';

export async function approveAndSend() {
    const { emailId } = getAuthState();
    const content = document.getElementById('ai-draft-body').innerHTML;

    // Get current thread and recipient from email manager
    const { currentThreadId, recipientEmail } = await import('./emailManager.js');
    
    if (!currentThreadId) return alert("Select an email first!");
    

    const response = await sendEmailAPI(emailId, currentThreadId, content, recipientEmail, false);
    
    if (!response) return;
    if (response.message_id) {
        document.getElementById('ai-draft-body').innerHTML = "<div style='color: green;'>Email sent successfully!</div>";
        document.getElementById('thread-content').innerHTML = '<div class="text-center text-muted mt-5">Select an email to view thread context</div>';
        await syncEmails();
    }
}

export async function draftEmail() {
    const { emailId } = getAuthState();
    const content = document.getElementById('ai-draft-body').innerHTML;

    
    // Get current thread and recipient from email manager
    const { currentThreadId, recipientEmail } = await import('./emailManager.js');
    
    if (!currentThreadId) return alert("Select an email first!");

    const response = await sendEmailAPI(emailId, currentThreadId, content, recipientEmail, true);
    
    if (!response) return;
    if (response.draft_id) {
        document.getElementById('ai-draft-body').innerHTML = "<div style='color: green;'>Draft Saved successfully!</div>";
        document.getElementById('thread-content').innerHTML = '<div class="text-center text-muted mt-5">Select an email to view thread context</div>';
        await syncEmails();
    }
}
