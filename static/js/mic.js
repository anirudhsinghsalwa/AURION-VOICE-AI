// Constants and DOM Elements
const micBtn = document.getElementById('mic-btn');
const textInput = document.getElementById('text-input');
const chatForm = document.getElementById('chat-form');
const chatViewport = document.getElementById('chat-viewport');
const statusText = document.getElementById('status-text');
const statusDot = document.getElementById('assistant-status').querySelector('.status-dot');
const ttsToggle = document.getElementById('tts-toggle');
const clearBtn = document.getElementById('clear-btn');
const welcomeScreen = document.getElementById('welcome-screen');

// Voice / Speech State
let recognition = null;
let isListening = false;
let speechUtterance = null;

// Initialize Speech Recognition
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        isListening = true;
        micBtn.classList.add('listening');
        document.querySelector('.voice-instruction').textContent = 'Listening...';
        updateStatus('Listening...', 'yellow');
        
        // Stop any currently playing TTS when user starts speaking
        if (window.speechSynthesis) {
            window.speechSynthesis.cancel();
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        resetMicUI();
        if (event.error === 'not-allowed') {
            updateStatus('Mic access denied', 'red');
            alert('Microphone access denied. Please enable microphone permissions in your browser settings.');
        } else {
            updateStatus('Speech error', 'red');
        }
    };

    recognition.onend = () => {
        resetMicUI();
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript && transcript.trim() !== '') {
            sendMessage(transcript);
        }
    };
} else {
    // Web Speech API not supported
    console.warn('Speech Recognition API not supported in this browser.');
    document.querySelector('.voice-instruction').textContent = 'Voice input not supported';
    micBtn.style.opacity = '0.5';
    micBtn.style.cursor = 'not-allowed';
    updateStatus('Voice input unsupported', 'red');
}

// Event Listeners
if (micBtn && recognition) {
    micBtn.addEventListener('click', () => {
        if (isListening) {
            recognition.stop();
        } else {
            try {
                recognition.start();
            } catch (err) {
                console.error('Failed to start recognition:', err);
            }
        }
    });
}

if (chatForm) {
    chatForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const text = textInput.value.trim();
        if (text) {
            sendMessage(text);
            textInput.value = '';
        }
    });
}

if (clearBtn) {
    clearBtn.addEventListener('click', clearConversation);
}

// Function to handle suggesting prompts
function useSuggestedPrompt(promptText) {
    sendMessage(promptText);
}

// Helper to update status indicators
function updateStatus(text, colorClass) {
    statusText.textContent = text;
    statusDot.className = 'status-dot ' + colorClass;
}

// Reset Mic UI back to ready
function resetMicUI() {
    isListening = false;
    if (micBtn) {
        micBtn.classList.remove('listening');
    }
    document.querySelector('.voice-instruction').textContent = 'Click to speak';
    updateStatus('Ready', 'green');
}

// Helper to get CSRF token from Django cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Send user message to Django backend
async function sendMessage(messageText) {
    // Hide welcome screen if present
    if (welcomeScreen) {
        welcomeScreen.remove();
    }

    // Append User Message to viewport
    appendMessage('user', messageText);
    updateStatus('Processing...', 'yellow');

    // Create placeholder for AI reply
    const aiMessageDiv = appendMessage('ai', 'Thinking...');
    const contentDiv = aiMessageDiv.querySelector('.message-content');

    try {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');

        const response = await fetch('/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({ message: messageText })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (data.error) {
            contentDiv.textContent = `Error: ${data.error}`;
            updateStatus('Error', 'red');
            return;
        }

        // Render formatted Markdown response
        const formattedHTML = formatMarkdown(data.reply);
        contentDiv.innerHTML = formattedHTML;
        updateStatus('AI Responding...', 'green');

        // Trigger Text-to-Speech if enabled
        if (ttsToggle && ttsToggle.checked) {
            speakResponse(data.reply);
        } else {
            updateStatus('Ready', 'green');
        }

    } catch (error) {
        console.error('Error fetching chat response:', error);
        contentDiv.textContent = 'Oops, something went wrong. Please check your connection or environment variables.';
        updateStatus('Error', 'red');
    }
}

// Append message bubbles to chat viewport
function appendMessage(role, text) {
    const row = document.createElement('div');
    row.className = `message-row ${role}`;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? 'U' : 'A';

    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';

    const content = document.createElement('div');
    content.className = 'message-content';
    
    if (role === 'user') {
        content.textContent = text;
    } else {
        content.innerHTML = text; // HTML for styled AI responses
    }

    bubble.appendChild(content);
    row.appendChild(avatar);
    row.appendChild(bubble);
    chatViewport.appendChild(row);

    // Auto-scroll to bottom of chat
    chatViewport.scrollTop = chatViewport.scrollHeight;

    return row;
}

// Speech Synthesis (TTS) Readback
function speakResponse(text) {
    if (!window.speechSynthesis) {
        console.warn('Text-to-speech not supported.');
        updateStatus('Ready', 'green');
        return;
    }

    // Cancel active voice playbacks
    window.speechSynthesis.cancel();

    // Strip Markdown structures/HTML tags to clean speakable text
    const cleanText = text
        .replace(/```[\s\S]*?```/g, '') // Remove code blocks
        .replace(/`([^`\n]+)`/g, '$1') // Remove inline code format
        .replace(/\*\*([^*]+)\*\*/g, '$1') // Remove bold markers
        .replace(/[*#-]/g, '') // Remove bullet formatting
        .replace(/<[^>]*>/g, '') // Remove HTML tags
        .trim();

    if (!cleanText) {
        updateStatus('Ready', 'green');
        return;
    }

    // Split text into smaller sentences if too long to prevent SpeechSynthesis timeouts
    speechUtterance = new SpeechSynthesisUtterance(cleanText);
    
    // Choose a premium sounding english voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferredVoice = voices.find(voice => 
        voice.name.includes('Google') && voice.lang.startsWith('en') || 
        voice.name.includes('Natural') && voice.lang.startsWith('en')
    );
    if (preferredVoice) {
        speechUtterance.voice = preferredVoice;
    }

    speechUtterance.onstart = () => {
        updateStatus('AI Speaking...', 'green');
    };

    speechUtterance.onend = () => {
        updateStatus('Ready', 'green');
    };

    speechUtterance.onerror = (e) => {
        console.error('SpeechSynthesis error:', e);
        updateStatus('Ready', 'green');
    };

    window.speechSynthesis.speak(speechUtterance);
}

// Clear chat history
async function clearConversation() {
    if (!confirm('Are you sure you want to clear the conversation history?')) {
        return;
    }

    // Cancel speech
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }

    try {
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || getCookie('csrftoken');
        const response = await fetch('/reset/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrftoken
            }
        });

        if (response.ok) {
            // Clear DOM
            chatViewport.innerHTML = `
                <div class="welcome-container" id="welcome-screen">
                    <div class="welcome-badge">Real-time Assistant</div>
                    <h2>How can I help you today?</h2>
                    <p>Click the microphone button to start speaking, or type your message in the box below.</p>
                    <div class="suggested-prompts">
                        <button class="prompt-chip" onclick="useSuggestedPrompt('Explain quantum computing in simple terms')">\"Explain quantum computing\"</button>
                        <button class="prompt-chip" onclick="useSuggestedPrompt('Write a python script to sort a list')">\"Write a sorting script\"</button>
                        <button class="prompt-chip" onclick="useSuggestedPrompt('Draft an email request for a project update')">\"Draft an email\"</button>
                    </div>
                </div>
            `;
            updateStatus('Ready', 'green');
        } else {
            console.error('Failed to clear conversation backend data.');
        }
    } catch (err) {
        console.error('Error clearing conversation:', err);
    }
}

// Basic Markdown-to-HTML Formatter
function formatMarkdown(text) {
    // Escape HTML to prevent XSS
    let escaped = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");

    // Code blocks: ```code```
    escaped = escaped.replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>');

    // Inline code: `code`
    escaped = escaped.replace(/`([^`\n]+)`/g, '<code>$1</code>');

    // Bold: **text**
    escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Bullet points: - item or * item
    let lines = escaped.split('\n');
    let inList = false;
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        if (line.startsWith('- ') || line.startsWith('* ')) {
            let content = line.substring(2);
            if (!inList) {
                lines[i] = '<ul><li>' + content + '</li>';
                inList = true;
            } else {
                lines[i] = '<li>' + content + '</li>';
            }
        } else {
            if (inList) {
                lines[i] = '</ul>' + lines[i];
                inList = false;
            }
        }
    }
    if (inList) {
        lines.push('</ul>');
    }
    escaped = lines.join('\n');

    // Paragraphs (split by double newlines)
    let parts = escaped.split(/\n\n+/);
    for (let i = 0; i < parts.length; i++) {
        let part = parts[i].trim();
        // Don't wrap tags like pre and ul in paragraph tags if they are separate components
        if (!part.startsWith('<pre>') && !part.startsWith('<ul>') && !part.startsWith('<li>') && !part.startsWith('</ul>')) {
            parts[i] = '<p>' + part.replace(/\n/g, '<br>') + '</p>';
        }
    }
    return parts.join('\n');
}

// Trigger voices list loading for SpeechSynthesis (some browsers require this)
if (window.speechSynthesis && window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = () => {};
}

// Auto Scroll to Bottom on page load if history is pre-rendered
window.addEventListener('DOMContentLoaded', () => {
    chatViewport.scrollTop = chatViewport.scrollHeight;
});
