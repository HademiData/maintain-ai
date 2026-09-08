const API_URL = "http://127.0.0.1:8000";


// ==========================================
// AUTHENTICATION
// ==========================================

const token =
    localStorage.getItem("maintain_ai_token");

const storedUser =
    localStorage.getItem("maintain_ai_user");


// Protect dashboard

if (
    window.location.pathname.includes("dashboard.html") &&
    !token
) {
    window.location.href = "login.html";
}


// ==========================================
// USER INFORMATION
// ==========================================

if (storedUser) {

    const user = JSON.parse(storedUser);

    const userName =
        document.getElementById("userName");

    const userEmail =
        document.getElementById("userEmail");

    const userAvatar =
        document.getElementById("userAvatar");


    if (userName) {
        userName.textContent =
            user.full_name;
    }

    if (userEmail) {
        userEmail.textContent =
            user.email;
    }

    if (userAvatar) {
        userAvatar.textContent =
            user.full_name
                .charAt(0)
                .toUpperCase();
    }
}


// ==========================================
// LOGIN
// ==========================================

const loginForm =
    document.getElementById("loginForm");

if (loginForm) {

    loginForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();


            const email =
                document
                    .getElementById("loginEmail")
                    .value
                    .trim();

            const password =
                document
                    .getElementById("loginPassword")
                    .value;


            const errorElement =
                document.getElementById("loginError");


            errorElement.textContent = "";


            try {

                const response =
                    await fetch(
                        `${API_URL}/auth/login`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                email,
                                password
                            })
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    errorElement.textContent =
                        data.detail ||
                        "Login failed.";

                    return;
                }


                localStorage.setItem(
                    "maintain_ai_token",
                    data.access_token
                );


                localStorage.setItem(
                    "maintain_ai_user",
                    JSON.stringify(data.user)
                );


                window.location.href =
                    "dashboard.html";

            }

            catch (error) {

                errorElement.textContent =
                    "Unable to connect to the server.";

            }

        }
    );
}


// ==========================================
// REGISTER
// ==========================================

const registerForm =
    document.getElementById("registerForm");

if (registerForm) {

    registerForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();


            const fullName =
                document
                    .getElementById("fullName")
                    .value
                    .trim();

            const email =
                document
                    .getElementById("email")
                    .value
                    .trim();

            const password =
                document
                    .getElementById("password")
                    .value;


            const errorElement =
                document.getElementById(
                    "registerError"
                );


            errorElement.textContent = "";


            try {

                const response =
                    await fetch(
                        `${API_URL}/auth/register`,
                        {
                            method: "POST",

                            headers: {
                                "Content-Type":
                                    "application/json"
                            },

                            body: JSON.stringify({
                                full_name: fullName,
                                email,
                                password
                            })
                        }
                    );


                const data =
                    await response.json();


                if (!response.ok) {

                    errorElement.textContent =
                        data.detail ||
                        "Registration failed.";

                    return;
                }


                localStorage.setItem(
                    "maintain_ai_token",
                    data.access_token
                );


                localStorage.setItem(
                    "maintain_ai_user",
                    JSON.stringify(data.user)
                );


                window.location.href =
                    "dashboard.html";

            }

            catch (error) {

                errorElement.textContent =
                    "Unable to connect to the server.";

            }

        }
    );
}


// ==========================================
// LOGOUT
// ==========================================

const logoutButton =
    document.getElementById("logoutButton");

if (logoutButton) {

    logoutButton.addEventListener(
        "click",
        () => {

            localStorage.removeItem(
                "maintain_ai_token"
            );

            localStorage.removeItem(
                "maintain_ai_user"
            );

            window.location.href =
                "login.html";

        }
    );
}


// ==========================================
// DASHBOARD NAVIGATION
// ==========================================

const navItems =
    document.querySelectorAll(".nav-item");


navItems.forEach((item) => {

    item.addEventListener(
        "click",
        () => {

            const page =
                item.dataset.page;


            navItems.forEach((nav) => {
                nav.classList.remove("active");
            });

            item.classList.add("active");


            document
                .querySelectorAll(".dashboard-page")
                .forEach((section) => {

                    section.classList.remove(
                        "active-page"
                    );

                });


            const selectedPage =
                document.getElementById(
                    `${page}Page`
                );


            if (selectedPage) {

                selectedPage.classList.add(
                    "active-page"
                );

            }

        }
    );

});


// ==========================================
// CONVERSATION
// ==========================================
let conversationId = null;

let activeConversationId = null;


if (token) {
    loadConversations();
}

// ==========================================
// CHAT
// ==========================================

const chatForm =
    document.getElementById("chatForm");

const chatInput =
    document.getElementById("chatInput");

const chatMessages =
    document.getElementById("chatMessages");

const sendButton =
    document.getElementById("sendButton");


if (chatForm) {

    chatForm.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            await sendMessage();

        }
    );

}


async function sendMessage() {

    const question = chatInput.value.trim();

    if (!question) {
        return;
    }

    if (!token) {
        console.error("User is not authenticated.");
        return;
    }

    sendButton.disabled = true;

    addUserMessage(question);

    chatInput.value = "";

    const loading = addLoadingMessage();

    try {

        // Create conversation if necessary
        if (!activeConversationId) {

            const conversationResponse =
                await fetch(
                    `${API_URL}/conversations`,
                    {
                        method: "POST",
                        headers: {
                            "Authorization":
                                `Bearer ${token}`
                        }
                    }
                );

            if (!conversationResponse.ok) {
                throw new Error(
                    "Failed to create conversation."
                );
            }

            const conversation =
                await conversationResponse.json();

            activeConversationId =
                conversation.conversation_id;

            conversationId =
                activeConversationId;

            localStorage.setItem(
                "maintain_ai_conversation_id",
                activeConversationId
            );
        }

        // Send question
        const response =
            await fetch(
                `${API_URL}/chat`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Authorization":
                            `Bearer ${token}`
                    },

                    body: JSON.stringify({
                        question: question,
                        conversation_id:
                            activeConversationId
                    })
                }
            );

        const data =
            await response.json();

        loading.remove();

        if (!response.ok) {

            addAIMessage(
                data.detail ||
                "Something went wrong."
            );

            return;
        }

        // Render structured response correctly
        renderAIResponse(data);

        // Refresh sidebar
        await loadConversations();

    }

    catch (error) {

        console.error(
            "Chat error:",
            error
        );

        loading.remove();

        addAIMessage(
            "Unable to connect to Maintain AI."
        );

    }

    finally {

        sendButton.disabled = false;

        chatInput.focus();

    }
}

// ==========================================
// ADD USER MESSAGE
// ==========================================

function addUserMessage(message) {

    const welcome =
        document.querySelector(
            ".welcome-message"
        );

    if (welcome) {
        welcome.remove();
    }


    const wrapper =
        document.createElement("div");

    wrapper.className =
        "chat-message user";


    const content =
        document.createElement("div");

    content.className =
        "chat-message-content";

    content.textContent =
        message;


    wrapper.appendChild(content);

    chatMessages.appendChild(wrapper);


    scrollChat();
}


// ==========================================
// ADD AI MESSAGE
// ==========================================

function addAIMessage(message) {

    const wrapper =
        document.createElement("div");

    wrapper.className =
        "chat-message ai";


    const content =
        document.createElement("div");

    content.className =
        "chat-message-content";


    const label =
        document.createElement("div");

    label.className =
        "ai-message-label";

    label.textContent =
        "✦ MAINTAIN AI";


    const text =
        document.createElement("div");

    text.textContent =
        message;


    content.appendChild(label);

    content.appendChild(text);

    wrapper.appendChild(content);

    chatMessages.appendChild(wrapper);


    scrollChat();
}


// ==========================================
// LOADING
// ==========================================

function addLoadingMessage() {

    const wrapper =
        document.createElement("div");

    wrapper.className =
        "chat-message ai";


    const content =
        document.createElement("div");

    content.className =
        "chat-message-content";


    content.innerHTML =
        `
        <div class="ai-message-label">
            ✦ MAINTAIN AI
        </div>

        <div>
            Thinking...
        </div>
        `;


    wrapper.appendChild(content);

    chatMessages.appendChild(wrapper);

    scrollChat();


    return wrapper;
}


// ==========================================
// RENDER AI RESPONSE
// ==========================================

function renderAIResponse(data) {

    if (
        data.type ===
        "maintenance_work_order"
    ) {

        renderWorkOrder(data);

        return;
    }


    addAIMessage(
        data.answer ||
        "No response was returned."
    );
}


// ==========================================
// WORK ORDER CARD
// ==========================================

function renderWorkOrder(data) {

    const wrapper =
        document.createElement("div");

    wrapper.className =
        "chat-message ai";


    const content =
        document.createElement("div");

    content.className =
        "chat-message-content";


    const equipment =
        data.equipment || {};

    const component =
        data.component || {};


    let partsHTML = "";


    if (
        data.required_parts &&
        data.required_parts.length
    ) {

        partsHTML =
            `
            <div class="parts-list">

                <h4>REQUIRED PARTS</h4>

                ${data.required_parts
                .map(
                    part => `
                        <div>
                            <span>
                                ${escapeHTML(part.name)}
                            </span>

                            <span>
                                ${escapeHTML(
                        part.item_number || "N/A"
                    )}
                            </span>
                        </div>
                        `
                )
                .join("")
            }

            </div>
            `;
    }


    let sourcesHTML = "";


    if (
        data.sources &&
        data.sources.length
    ) {

        sourcesHTML =
            `
            <div class="source-list">
                Sources:
                ${data.sources
                .map(
                    source =>
                        escapeHTML(source)
                )
                .join(", ")
            }
            </div>
            `;
    }


    content.innerHTML =
        `
        <div class="ai-message-label">
            ✦ MAINTAIN AI
        </div>

        <div class="work-order-card">

            <div class="work-order-header">

                <h3>
                    Maintenance Work Order
                </h3>

            </div>


            <div class="work-order-body">

                <div class="work-order-meta">

                    <div>
                        <small>EQUIPMENT</small>
                        <strong>
                            ${escapeHTML(
            equipment.name || "N/A"
        )}
                        </strong>
                    </div>

                    <div>
                        <small>ASSET</small>
                        <strong>
                            ${escapeHTML(
            equipment.item_number || "N/A"
        )}
                        </strong>
                    </div>

                    <div>
                        <small>COMPONENT</small>
                        <strong>
                            ${escapeHTML(
            component.name || "N/A"
        )}
                        </strong>
                    </div>

                </div>


                <div class="work-order-task">

                    <small>RECOMMENDED TASK</small>

                    <p>
                        ${escapeHTML(
            data.task || "N/A"
        )}
                    </p>

                </div>


                ${partsHTML}

                ${sourcesHTML}

            </div>

        </div>
        `;


    wrapper.appendChild(content);

    chatMessages.appendChild(wrapper);


    scrollChat();
}


// ==========================================
// SUGGESTIONS
// ==========================================

document
    .querySelectorAll(".suggestion")
    .forEach((button) => {

        button.addEventListener(
            "click",
            () => {

                const question =
                    button.dataset.question;

                if (chatInput) {

                    chatInput.value =
                        question;

                    chatInput.focus();

                }

            }
        );

    });


// ==========================================
// OPEN ASSISTANT
// ==========================================

function openAssistant() {

    const assistant =
        document.querySelector(
            '[data-page="assistant"]'
        );

    if (assistant) {
        assistant.click();
    }

}


function openAssistantWithQuestion(question) {

    openAssistant();

    setTimeout(() => {

        if (chatInput) {

            chatInput.value =
                question;

            chatInput.focus();

        }

    }, 100);

}


// ==========================================
// UTILITIES
// ==========================================

function scrollChat() {

    if (chatMessages) {

        chatMessages.scrollTop =
            chatMessages.scrollHeight;

    }

}


function escapeHTML(value) {

    const div =
        document.createElement("div");

    div.textContent =
        value ?? "";

    return div.innerHTML;

}


async function loadConversations() {

    const list =
        document.getElementById(
            "conversationList"
        );

    if (!list || !token) {
        return;
    }

    try {

        const response = await fetch(
            `${API_URL}/conversations`,
            {
                headers: {
                    "Authorization":
                        `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            throw new Error(
                "Failed to load conversations"
            );
        }

        const conversations =
            await response.json();

        renderConversationList(
            conversations
        );

    } catch (error) {

        console.error(
            "Conversation loading error:",
            error
        );

        list.innerHTML = `
            <div class="conversation-empty">
                Unable to load chats.
            </div>
        `;
    }
}

function renderConversationList(
    conversations
) {

    const list =
        document.getElementById(
            "conversationList"
        );

    if (!list) {
        return;
    }

    if (!conversations.length) {

        list.innerHTML = `
            <div class="conversation-empty">
                No previous chats yet.
            </div>
        `;

        return;
    }

    list.innerHTML = conversations
        .map(
            conversation => `
                <button
                    class="conversation-item ${conversation.conversation_id ===
                    activeConversationId
                    ? "active"
                    : ""
                }"
                    data-conversation-id="${escapeHTML(
                    conversation.conversation_id
                )
                }"
                >

                    <span class="conversation-icon">
                        ◌
                    </span>

                    <span class="conversation-title">
                        ${escapeHTML(
                    conversation.title
                )}
                    </span>

                </button>
            `
        )
        .join("");

    document
        .querySelectorAll(
            ".conversation-item"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                () => {

                    loadConversation(
                        button.dataset
                            .conversationId
                    );

                }
            );

        });
}

async function loadConversation(
    conversationIdToLoad
) {

    try {

        const response = await fetch(
            `${API_URL}/conversations/${conversationIdToLoad}`,
            {
                headers: {
                    "Authorization":
                        `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            throw new Error(
                "Failed to load conversation"
            );
        }

        const data =
            await response.json();

        activeConversationId =
            conversationIdToLoad;

        conversationId =
            conversationIdToLoad;

        localStorage.setItem(
            "maintain_ai_conversation_id",
            conversationIdToLoad
        );

        renderConversationMessages(
            data.messages
        );

        loadConversations();

        openAssistant();

    } catch (error) {

        console.error(
            "Conversation loading error:",
            error
        );

    }
}


function renderConversationMessages(
    messages
) {

    if (!chatMessages) {
        return;
    }

    chatMessages.innerHTML = "";

    messages.forEach(message => {

        if (message.role === "user") {

            addUserMessage(
                message.content
            );

        } else if (
            message.role === "assistant"
        ) {

            addAIMessage(
                message.content
            );

        }

    });

    scrollChat();
}

async function createNewChat() {

    try {

        const response = await fetch(
            `${API_URL}/conversations`,
            {
                method: "POST",

                headers: {
                    "Authorization":
                        `Bearer ${token}`
                }
            }
        );

        if (!response.ok) {
            throw new Error(
                "Failed to create conversation"
            );
        }

        const data =
            await response.json();

        activeConversationId =
            data.conversation_id;

        conversationId =
            data.conversation_id;

        localStorage.setItem(
            "maintain_ai_conversation_id",
            data.conversation_id
        );

        chatMessages.innerHTML = `
            <div class="welcome-message">

                <div class="welcome-icon">
                    ✦
                </div>

                <h2>
                    How can I help?
                </h2>

                <p>
                    Ask Maintain AI about your
                    equipment, maintenance,
                    troubleshooting or engineering.
                </p>

            </div>
        `;

        loadConversations();

        openAssistant();

        chatInput.focus();

    } catch (error) {

        console.error(
            "New conversation error:",
            error
        );

    }
}

const newChatButton =
    document.getElementById(
        "newChatButton"
    );

if (newChatButton) {

    newChatButton.addEventListener(
        "click",
        createNewChat
    );
}

