/**
 * UniAssist - "Ask First" Frontend Client Logic
 * Clean, modular vanilla JS managing chat streaming, citations,
 * follow-ups, feedback, escalation modal, and theme persistence.
 */

// ── 1. Application State ───────────────────────────────────────────────────
const state = {
    sessionId: getOrCreateSessionId(),
    theme: getInitialTheme(),
    isStreaming: false,
    abortController: null,
    lastUserQuestion: '',
    isChatState: false,
};

// ── 2. Session ID Management ───────────────────────────────────────────────
function getOrCreateSessionId() {
    try {
        let sid = sessionStorage.getItem('uniassist_session_id');
        if (!sid) {
            sid = 'sess_' + Math.random().toString(36).substring(2, 10) + '_' + Date.now();
            sessionStorage.setItem('uniassist_session_id', sid);
        }
        return sid;
    } catch (e) {
        return 'sess_fallback_' + Date.now();
    }
}

// ── 3. Theme Management ────────────────────────────────────────────────────
function getInitialTheme() {
    try {
        const stored = localStorage.getItem('uniassist_theme');
        if (stored === 'dark' || stored === 'light') return stored;
    } catch (e) {}

    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
    }
    return 'light';
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    state.theme = theme;
    try {
        localStorage.setItem('uniassist_theme', theme);
    } catch (e) {}
}

function toggleTheme() {
    const nextTheme = state.theme === 'dark' ? 'light' : 'dark';
    applyTheme(nextTheme);
}

// ── 4. Lifecycle & Initialization ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    applyTheme(state.theme);

    // Theme toggle button
    const themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) {
        themeBtn.addEventListener('click', toggleTheme);
    }

    // Modal keyboard trap and Escape to close
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const modal = document.getElementById('ticket-modal');
            if (modal && modal.style.display !== 'none') {
                closeTicketModal();
            }
        }
    });

    // Window scroll tracking for scroll-to-bottom button
    window.addEventListener('scroll', handleScrollDebounced);

    // Initial focus on hero input
    const heroInput = document.getElementById('hero-input');
    if (heroInput) {
        heroInput.focus();
    }
});

// ── 5. State Transitions (Home vs Chat) ────────────────────────────────────
function switchToChatState() {
    if (state.isChatState) return;
    state.isChatState = true;

    const homeView = document.getElementById('home-view');
    const chatView = document.getElementById('chat-view');
    const composer = document.getElementById('bottom-composer-wrap');

    if (homeView) homeView.style.display = 'none';
    if (chatView) chatView.style.display = 'flex';
    if (composer) composer.style.display = 'block';

    const chatInput = document.getElementById('chat-input');
    if (chatInput) chatInput.focus();
}

async function clearChatToHome() {
    if (state.isStreaming) stopGenerating();

    try {
        await fetch('/api/session/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.sessionId }),
        });
    } catch (e) {}

    const messageList = document.getElementById('message-list');
    if (messageList) messageList.innerHTML = '';

    state.isChatState = false;
    const homeView = document.getElementById('home-view');
    const chatView = document.getElementById('chat-view');
    const composer = document.getElementById('bottom-composer-wrap');

    if (homeView) homeView.style.display = 'flex';
    if (chatView) chatView.style.display = 'none';
    if (composer) composer.style.display = 'none';

    const heroInput = document.getElementById('hero-input');
    if (heroInput) {
        heroInput.value = '';
        heroInput.focus();
    }
    showToast('Chat cleared');
}

async function startNewSession() {
    if (state.isStreaming) stopGenerating();

    try {
        await fetch('/api/session/clear', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: state.sessionId }),
        });
    } catch (e) {}

    try {
        sessionStorage.removeItem('uniassist_session_id');
    } catch (e) {}

    state.sessionId = getOrCreateSessionId();
    const messageList = document.getElementById('message-list');
    if (messageList) messageList.innerHTML = '';

    showToast('New session started');
}

// ── 6. Input & Submission Handlers ─────────────────────────────────────────
function handleHeroSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('hero-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text || state.isStreaming) return;
    input.value = '';
    submitUserQuery(text);
}

function handleStickySubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text || state.isStreaming) return;
    input.value = '';
    autoResizeTextarea(input);
    submitUserQuery(text);
}

function handleTextareaKeydown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleStickySubmit(e);
    }
}

function autoResizeTextarea(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function sendTopicMessage(questionText) {
    if (state.isStreaming) return;
    submitUserQuery(questionText);
}

// ── 7. Message Pipeline & SSE Streaming ────────────────────────────────────
async function submitUserQuery(userQuery) {
    state.lastUserQuestion = userQuery;
    switchToChatState();

    // 1. Render User Message
    appendUserBubble(userQuery);
    scrollToBottom(true);

    // 2. Prepare Bot Message Container with Typing Indicator
    const botContainer = createBotMessageContainer();
    setStreamingState(true);

    // 3. Initiate Streaming Request
    state.abortController = new AbortController();

    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: userQuery,
                session_id: state.sessionId,
            }),
            signal: state.abortController.signal,
        });

        if (!response.ok) {
            throw new Error(`HTTP error ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let accumulatedAnswer = '';
        let sourcesData = [];
        let metaData = {};
        let chatLogId = null;
        let buffer = '';

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const blocks = buffer.split('\n\n');
            buffer = blocks.pop() || '';

            for (const block of blocks) {
                if (!block.trim()) continue;
                let eventType = 'message';
                let dataStr = '';

                for (const line of block.split('\n')) {
                    if (line.startsWith('event: ')) {
                        eventType = line.replace('event: ', '').trim();
                    } else if (line.startsWith('data: ')) {
                        dataStr = line.replace('data: ', '').trim();
                    }
                }

                if (eventType === 'token') {
                    try {
                        const token = JSON.parse(dataStr);
                        accumulatedAnswer += token;
                        botContainer.bubble.innerHTML = sanitizeMarkdown(accumulatedAnswer);
                        scrollToBottom(false);
                    } catch (e) {}
                } else if (eventType === 'sources') {
                    try {
                        sourcesData = JSON.parse(dataStr);
                        renderCitations(botContainer.citationsWrap, sourcesData);
                    } catch (e) {}
                } else if (eventType === 'meta') {
                    try {
                        metaData = JSON.parse(dataStr);
                    } catch (e) {}
                } else if (eventType === 'chat_log_id') {
                    try {
                        chatLogId = JSON.parse(dataStr);
                    } catch (e) {}
                }
            }
        }

        // Final markdown render and post-stream attachments
        botContainer.bubble.innerHTML = sanitizeMarkdown(accumulatedAnswer || 'No response received.');

        // Check if low-confidence fallback was triggered
        if (metaData.is_fallback) {
            renderFallbackCard(botContainer.metaBlock);
        }

        // Render follow-ups
        if (metaData.follow_up_suggestions && metaData.follow_up_suggestions.length > 0) {
            renderFollowUps(botContainer.followupsWrap, metaData.follow_up_suggestions);
        }

        // Render action buttons (Copy + Feedback)
        renderActions(botContainer.actionsWrap, userQuery, accumulatedAnswer, sourcesData, chatLogId);

    } catch (err) {
        if (err.name === 'AbortError') {
            botContainer.bubble.innerHTML += '<p style="color: var(--text-muted); font-size: 13px; margin-top: 8px;"><em>Generation stopped.</em></p>';
        } else {
            console.error('Chat stream failed:', err);
            renderErrorBubble(botContainer.container, userQuery);
        }
    } finally {
        setStreamingState(false);
        scrollToBottom(true);
    }
}

function setStreamingState(isStreaming) {
    state.isStreaming = isStreaming;
    const stopBtn = document.getElementById('stop-btn');
    const chatSubmitBtn = document.getElementById('chat-submit-btn');
    const chatInput = document.getElementById('chat-input');

    if (stopBtn) stopBtn.style.display = isStreaming ? 'inline-flex' : 'none';
    if (chatSubmitBtn) chatSubmitBtn.style.display = isStreaming ? 'none' : 'inline-flex';
    if (chatInput) {
        chatInput.disabled = isStreaming;
        if (!isStreaming) chatInput.focus();
    }
}

function stopGenerating() {
    if (state.abortController) {
        state.abortController.abort();
    }
}

// ── 8. DOM Message Builders ────────────────────────────────────────────────
function appendUserBubble(text) {
    const list = document.getElementById('message-list');
    const row = document.createElement('div');
    row.className = 'message-row user';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;

    row.appendChild(bubble);
    list.appendChild(row);
}

function createBotMessageContainer() {
    const list = document.getElementById('message-list');
    const row = document.createElement('div');
    row.className = 'message-row bot';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = `
        <div class="typing-indicator" aria-label="UniAssist is thinking">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    `;

    const metaBlock = document.createElement('div');
    metaBlock.className = 'bot-meta-block';

    const citationsWrap = document.createElement('div');
    citationsWrap.className = 'citations-wrap';

    const actionsWrap = document.createElement('div');
    actionsWrap.className = 'actions-wrap';

    const followupsWrap = document.createElement('div');
    followupsWrap.className = 'followups-wrap';

    metaBlock.appendChild(citationsWrap);
    metaBlock.appendChild(actionsWrap);
    metaBlock.appendChild(followupsWrap);

    row.appendChild(bubble);
    row.appendChild(metaBlock);
    list.appendChild(row);

    return {
        container: row,
        bubble,
        metaBlock,
        citationsWrap,
        actionsWrap,
        followupsWrap,
    };
}

function renderCitations(container, sources) {
    if (!sources || sources.length === 0) return;
    container.innerHTML = '';

    sources.forEach(src => {
        const chip = document.createElement('span');
        chip.className = 'citation-chip';
        const docTitle = src.document || src.title || 'Official Document';
        const section = src.section ? ` · ${src.section}` : '';
        chip.title = `Source citation (score: ${(src.score ?? 0).toFixed(2)})`;
        chip.innerHTML = `
            <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
            <span>${escapeHtml(docTitle)}${escapeHtml(section)}</span>
        `;
        container.appendChild(chip);
    });
}

function renderActions(container, question, answer, sources, chatLogId) {
    container.innerHTML = '';

    // Copy Button
    const copyBtn = document.createElement('button');
    copyBtn.className = 'feedback-btn';
    copyBtn.setAttribute('aria-label', 'Copy answer text');
    copyBtn.title = 'Copy answer';
    copyBtn.innerHTML = `
        <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
        </svg>
        <span>Copy</span>
    `;
    copyBtn.onclick = () => {
        navigator.clipboard.writeText(answer).then(() => {
            copyBtn.innerHTML = `
                <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <polyline points="20 6 9 17 4 12"/>
                </svg>
                <span>Copied</span>
            `;
            setTimeout(() => {
                copyBtn.innerHTML = `
                    <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                    </svg>
                    <span>Copy</span>
                `;
            }, 2500);
            showToast('Answer copied to clipboard');
        });
    };

    // Thumbs Up Button
    const upBtn = document.createElement('button');
    upBtn.className = 'feedback-btn';
    upBtn.setAttribute('aria-label', 'Helpful response');
    upBtn.title = 'Helpful';
    upBtn.innerHTML = `
        <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"/>
        </svg>
        <span>Helpful</span>
    `;

    // Thumbs Down Button
    const downBtn = document.createElement('button');
    downBtn.className = 'feedback-btn';
    downBtn.setAttribute('aria-label', 'Unhelpful response');
    downBtn.title = 'Not helpful';
    downBtn.innerHTML = `
        <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h3a2 2 0 0 1 2 2v7a2 2 0 0 1-2 2h-3"/>
        </svg>
        <span>Not helpful</span>
    `;

    upBtn.onclick = () => submitFeedback(upBtn, downBtn, container, 'up', question, answer, sources, chatLogId);
    downBtn.onclick = () => submitFeedback(downBtn, upBtn, container, 'down', question, answer, sources, chatLogId);

    container.appendChild(copyBtn);
    container.appendChild(upBtn);
    container.appendChild(downBtn);
}

async function submitFeedback(activeBtn, otherBtn, container, rating, question, answer, sources, chatLogId) {
    activeBtn.disabled = true;
    otherBtn.disabled = true;

    if (rating === 'up') {
        activeBtn.classList.add('active-positive');
    } else {
        activeBtn.classList.add('active-negative');
    }

    // Visible confirmation text
    const statusText = document.createElement('span');
    statusText.className = 'feedback-status-text';
    statusText.textContent = 'Thanks for the feedback!';
    container.appendChild(statusText);

    try {
        await fetch('/api/feedback', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                session_id: state.sessionId,
                chat_log_id: chatLogId,
                question: question,
                answer: answer,
                sources: typeof sources === 'string' ? sources : JSON.stringify(sources || []),
                rating: rating,
            }),
        });
    } catch (e) {
        console.warn('Feedback submission failed:', e);
    }
}

function renderFollowUps(container, suggestions) {
    if (!suggestions || suggestions.length === 0) return;
    container.innerHTML = '';

    suggestions.forEach(sug => {
        const pill = document.createElement('button');
        pill.className = 'followup-pill';
        pill.type = 'button';
        pill.textContent = sug;
        pill.onclick = () => sendTopicMessage(sug);
        container.appendChild(pill);
    });
}

function renderFallbackCard(metaBlock) {
    const card = document.createElement('div');
    card.className = 'fallback-card';
    card.innerHTML = `
        <div class="fallback-card-title">I couldn't find this in the official documents.</div>
        <div class="fallback-card-desc">Would you like to connect with university administration directly?</div>
        <div>
            <button type="button" class="btn btn-secondary btn-sm" onclick="openTicketModal()" style="font-size: 13px; min-height: 36px; padding: 6px 14px;">
                <svg class="icon icon-sm" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M2 9a3 3 0 0 1 0 6v2a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-2a3 3 0 0 1 0-6V7a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v2z"/>
                </svg>
                <span>Create a support ticket</span>
            </button>
        </div>
    `;
    metaBlock.prepend(card);
}

function renderErrorBubble(container, originalQuery) {
    const errorRow = document.createElement('div');
    errorRow.className = 'error-bubble';
    errorRow.innerHTML = `
        <span>Sorry, connection error occurred. Please check your network.</span>
        <button type="button" class="btn btn-secondary" style="min-height: 32px; padding: 4px 12px; font-size: 13px;">Retry</button>
    `;
    const retryBtn = errorRow.querySelector('button');
    retryBtn.onclick = () => {
        errorRow.remove();
        submitUserQuery(originalQuery);
    };
    container.appendChild(errorRow);
}

// ── 9. Markdown & Sanitization ─────────────────────────────────────────────
function sanitizeMarkdown(rawText) {
    if (typeof marked !== 'undefined' && typeof DOMPurify !== 'undefined') {
        const parsedHtml = marked.parse(rawText || '', { breaks: true });
        return DOMPurify.sanitize(parsedHtml);
    }
    return escapeHtml(rawText).replace(/\n/g, '<br>');
}

function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

// ── 10. Scroll Control ─────────────────────────────────────────────────────
function scrollToBottom(smooth = false) {
    const scrollHeight = document.documentElement.scrollHeight;
    window.scrollTo({
        top: scrollHeight,
        behavior: smooth ? 'smooth' : 'instant',
    });
}

function handleScrollDebounced() {
    const scrollBtn = document.getElementById('scroll-bottom-btn');
    if (!scrollBtn || !state.isChatState) return;

    const scrollPos = window.scrollY + window.innerHeight;
    const totalHeight = document.documentElement.scrollHeight;
    // Show button if more than 200px from bottom
    if (totalHeight - scrollPos > 200) {
        scrollBtn.style.display = 'inline-flex';
    } else {
        scrollBtn.style.display = 'none';
    }
}

// ── 11. Escalation Modal Dialog Logic ──────────────────────────────────────
let previousActiveElement = null;

function openTicketModal() {
    previousActiveElement = document.activeElement;
    const modal = document.getElementById('ticket-modal');
    const modalCard = document.getElementById('modal-card');
    const ticketForm = document.getElementById('ticket-form');
    const successView = document.getElementById('ticket-success-view');
    const errorDiv = document.getElementById('modal-error');

    if (!modal) return;

    // Reset views
    if (ticketForm) ticketForm.style.display = 'block';
    if (successView) successView.style.display = 'none';
    if (errorDiv) errorDiv.style.display = 'none';

    // Pre-fill question with last user question if available
    const queryInput = document.getElementById('ticket-query');
    if (queryInput && state.lastUserQuestion && !queryInput.value) {
        queryInput.value = state.lastUserQuestion;
    }

    modal.style.display = 'flex';
    if (modalCard) modalCard.focus();
}

function closeTicketModal() {
    const modal = document.getElementById('ticket-modal');
    if (modal) modal.style.display = 'none';
    if (previousActiveElement && typeof previousActiveElement.focus === 'function') {
        previousActiveElement.focus();
    }
}

async function handleTicketSubmit(e) {
    e.preventDefault();
    const nameInput = document.getElementById('ticket-name');
    const sidInput = document.getElementById('ticket-sid');
    const emailInput = document.getElementById('ticket-email');
    const queryInput = document.getElementById('ticket-query');
    const submitBtn = document.getElementById('ticket-submit-btn');
    const errorDiv = document.getElementById('modal-error');

    const name = nameInput?.value.trim();
    const student_id = sidInput?.value.trim();
    const email = emailInput?.value.trim();
    const query = queryInput?.value.trim();

    if (!name || !student_id || !email || !query) {
        if (errorDiv) {
            errorDiv.textContent = 'Please complete all required fields.';
            errorDiv.style.display = 'block';
        }
        return;
    }

    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
    }
    if (errorDiv) errorDiv.style.display = 'none';

    try {
        const res = await fetch('/api/tickets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, student_id, email, query }),
        });

        if (!res.ok) {
            throw new Error(`Server returned ${res.status}`);
        }

        const data = await res.json();
        document.getElementById('ticket-form').style.display = 'none';
        const successView = document.getElementById('ticket-success-view');
        successView.style.display = 'block';
        document.getElementById('success-ticket-id').textContent = data.ticket_id;

        // Reset form inputs for future
        nameInput.value = '';
        sidInput.value = '';
        emailInput.value = '';
        queryInput.value = '';

    } catch (err) {
        console.error('Ticket creation error:', err);
        if (errorDiv) {
            errorDiv.textContent = 'Failed to submit ticket. Please check connection and retry.';
            errorDiv.style.display = 'block';
        }
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit ticket';
        }
    }
}

function copyTicketId() {
    const idEl = document.getElementById('success-ticket-id');
    if (!idEl) return;
    navigator.clipboard.writeText(idEl.textContent.trim()).then(() => {
        showToast('Ticket ID copied to clipboard');
    });
}

// ── 12. Toast Feedback ─────────────────────────────────────────────────────
let toastTimeout = null;

function showToast(message) {
    const toast = document.getElementById('toast');
    if (!toast) return;

    if (toastTimeout) clearTimeout(toastTimeout);
    toast.textContent = message;
    toast.style.display = 'block';

    toastTimeout = setTimeout(() => {
        toast.style.display = 'none';
    }, 2800);
}
