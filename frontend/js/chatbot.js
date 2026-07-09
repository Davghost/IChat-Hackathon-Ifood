const chatInput = document.getElementById("chatInput");
const sendButton = document.getElementById("sendMessage");
const chatBody = document.getElementById("chatBody");

document.addEventListener("DOMContentLoaded", () => {

    const chatButton = document.getElementById("chatButton");
    const chatOverlay = document.getElementById("chatOverlay");
    const chatClose = document.querySelector(".chat-close");

    if (!chatButton || !chatOverlay) return;

    chatButton.addEventListener("click", () => {
        chatOverlay.classList.add("active");
    });

    if (chatClose) {
        chatClose.addEventListener("click", () => {
            chatOverlay.classList.remove("active");
            chatBody.innerHTML = `
        <div class="message bot">
             Olá! 👋<br> Como posso ajudar você hoje?
        </div>
    `
           
        });
        
    }

    chatOverlay.addEventListener("click", (event) => {
        if (event.target === chatOverlay) {
            chatOverlay.classList.remove("active");
        }
    });

});

function sendMessage() {

    const text = chatInput.value.trim();

    if (text === "") return;

    chatBody.innerHTML += `
        <div class="message user">
            ${text}
        </div>
    `;

    chatInput.value = "";

    setTimeout(() => {

        chatBody.innerHTML += `
            <div class="message bot">
                Recebi sua mensagem: "${text}"
            </div>
        `;

        chatBody.scrollTop = chatBody.scrollHeight;

    }, 500);

}

sendButton.addEventListener("click", sendMessage);

chatInput.addEventListener("keypress", function(e){

    if(e.key === "Enter"){

        sendMessage();

    }

});
