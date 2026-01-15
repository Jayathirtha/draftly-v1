// Email Management Module

import { fetchLatestEmails, fetchEmailThread, regenerateDraftAPI, sendEmailAPI } from './api.js';
import { getAuthState } from './auth.js';

export let currentThreadId = null;
export let emailThreadContentData = {};
export let recipientEmail = "";
export let fromEmail = "";
export let toEmail = "";

const AUTO_REFRESH_INTERVAL = 2 * 60 * 1000; // 2 minutes

export function startAutoPolling() {
    console.log("Auto-polling started...");
    setInterval(async () => {
        const { isLoggedIn } = getAuthState();
        if (isLoggedIn) {
            console.log("refresh to sync emails...");
            await syncEmails();
        }
    }, AUTO_REFRESH_INTERVAL);
}

export async function syncEmails() {
    const { emailId } = getAuthState();
    const listContainer = document.getElementById('email-list');
    const syncTimeDisplay = document.getElementById('last-sync-time');
    
    listContainer.innerHTML = '<div class="p-3 text-center">Syncing...</div>';
    syncTimeDisplay.innerText = "Syncing...";
    syncTimeDisplay.classList.remove('text-danger');
    
    try {
        const data  = await fetchLatestEmails(emailId);
        if (!data) return;

        const now = new Date();
        syncTimeDisplay.innerText = now.toLocaleTimeString([], 
            { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        const messages = data.messages || data.message_ids;
        if(typeof(data.message) == "string") 
        {
            listContainer.innerHTML = `<div class="p-3 text-center">${data.message}</div>`;
            return;
        }
        
        const subjects = messages.subject;
        if (!messages || !subjects) {
            listContainer.innerHTML = '<div class="p-3 text-center">No emails found</div>';
            return;
        }
        
        
        const msgIds = messages.msgId;
        const threadIds = messages.threadId;
        const from = messages.from || "Unknown Sender";
        const snippet = messages.snippet || [];
        const toEmail = messages.toEmail || [];
        
        const emailList = msgIds.map((msgId, index) => ({
            msgId: msgId,
            threadId: threadIds[index],
            subject: subjects[index],
            from: from[index] || "Unknown Sender",
            snippet: snippet[index] || "",
            toEmail: toEmail[index]
        }));
        
        console.log("Processed emails:", emailList);
        renderEmailList(emailList, listContainer);
        
    } catch (err) {
        console.error("Sync failed", err);
        syncTimeDisplay.innerText = "Error";
        syncTimeDisplay.classList.add('text-danger');
        listContainer.innerHTML = '<div class="p-3 text-center text-danger">Failed to sync emails</div>';
    }
}

function renderEmailList(emailList, container) {
    container.innerHTML = '';
    emailList.forEach(email => {
        const item = document.createElement('div');
        item.className = 'list-group-item email-item p-3';
        item.onclick = () => loadThread(email.threadId, email.subject, email.from);
        item.innerHTML = `
            <div class="d-flex justify-content-between"><strong>${email.subject}</strong></div>
            <div class="small text-truncate">${email.from}</div>
            <div class="small text-truncate">${email.snippet}</div>
        `;
        container.appendChild(item);
    });
}

export async function loadThread(threadId, subject, from) {
    const { emailId, draftTone } = getAuthState();
    currentThreadId = threadId;
    recipientEmail = from;
    
    document.getElementById('view-subject').innerText = subject;
    const draftArea = document.getElementById('ai-draft-body');
    const threadContent = document.getElementById('thread-content');
    
    threadContent.innerHTML = 'Loading conversation...';
    draftArea.innerHTML = "AI is thinking...";
    
    try {
        emailThreadContentData = await fetchEmailThread(emailId, threadId, draftTone || 'Professional');
        if (!emailThreadContentData) return;
        
        const draft = emailThreadContentData.draft || "No draft generated. retry again.";
        const threadMsgs = emailThreadContentData.thread_context?.llm_context || [];
        fromEmail = emailThreadContentData.thread_context?.llm_context.from_email || "";
        toEmail = emailThreadContentData.thread_context?.llm_context.to_email || "";

        threadContent.innerHTML = threadMsgs.map(msg => `
            <div class="mb-3 p-2 border-bottom">
                <div class="d-flex justify-content-between">
                    <strong>${msg.from || 'Unknown'}</strong>
                    <small class="text-muted">${msg.date || ''}</small>
                </div>
                <div class="small text-muted">To: ${msg.to || 'Unknown'}</div>
                <p class="mb-0 mt-2">${msg.body || 'No content'}</p>
            </div>
        `).join('');

        draftArea.innerHTML = draft;
        
    } catch (err) {
        console.error("Thread fetch failed", err);
        draftArea.innerHTML = "Failed to generate draft.";
    }
}

export async function regenerateDraft(tone) {
    const draftArea = document.getElementById('ai-draft-body');
    draftArea.innerHTML = "AI is thinking...";
    
    const threadMsgs = emailThreadContentData.thread_context?.llm_context || [];
    const llmContext = threadMsgs.map(msg => msg.body || 'No content');
    
    try {
        const data  = await regenerateDraftAPI(tone, currentThreadId);
        if (!data) return;
        
       
        const draft = data.draft || "No draft generated. retry again.";
        draftArea.innerHTML = draft;
        draftArea.contentEditable = "true";
        
    } catch (err) {
        console.error("Regenerate failed", err);
        draftArea.innerHTML = "Failed to generate draft.";
    }
}
