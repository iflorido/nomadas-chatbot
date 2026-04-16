/**
 * chat.js — Widget de chatbot para WordPress (Nomadas Surf Park)
 * Incluir en functions.php o con un plugin de snippets:
 *   wp_enqueue_script('nomadas-chat', get_template_directory_uri().'/chat.js', [], '1.0', true);
 * O añadir directamente en footer.php antes de </body>
 */

(function () {
  const API_URL = "https://chat.nomadassurfpark.com/chat"; // ← cambia esto

  const style = document.createElement("style");
  style.textContent = `
    #nomadas-chat-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 9999;
      width: 60px; height: 60px; border-radius: 50%;
      background: #0077b6; color: #fff; border: none; cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,119,182,.45);
      font-size: 28px; display: flex; align-items: center; justify-content: center;
      transition: transform .2s;
    }
    #nomadas-chat-btn:hover { transform: scale(1.08); }
    #nomadas-chat-box {
      position: fixed; bottom: 96px; right: 24px; z-index: 9998;
      width: 360px; max-height: 520px;
      background: #fff; border-radius: 16px;
      box-shadow: 0 8px 32px rgba(0,0,0,.18);
      display: none; flex-direction: column; overflow: hidden;
      font-family: 'Segoe UI', sans-serif;
    }
    #nomadas-chat-box.open { display: flex; }
    #nomadas-chat-header {
      background: #0077b6; color: #fff;
      padding: 14px 18px; font-weight: 600; font-size: 15px;
      display: flex; align-items: center; gap: 10px;
    }
    #nomadas-chat-header span.dot {
      width: 10px; height: 10px; border-radius: 50%;
      background: #90e0ef; display: inline-block;
    }
    #nomadas-chat-messages {
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 10px;
    }
    .nc-msg {
      max-width: 82%; padding: 10px 14px;
      border-radius: 14px; font-size: 14px; line-height: 1.5;
      white-space: pre-wrap;
    }
    .nc-msg.bot  { background: #f0f4f8; align-self: flex-start; border-bottom-left-radius: 4px; }
    .nc-msg.user { background: #0077b6; color: #fff; align-self: flex-end; border-bottom-right-radius: 4px; }
    .nc-msg.typing { color: #aaa; font-style: italic; }
    #nomadas-chat-input-row {
      display: flex; padding: 10px 12px; gap: 8px;
      border-top: 1px solid #eee;
    }
    #nomadas-chat-input {
      flex: 1; border: 1px solid #ddd; border-radius: 20px;
      padding: 8px 14px; font-size: 14px; outline: none;
      resize: none; max-height: 80px;
    }
    #nomadas-chat-input:focus { border-color: #0077b6; }
    #nomadas-chat-send {
      background: #0077b6; color: #fff; border: none;
      border-radius: 50%; width: 38px; height: 38px;
      cursor: pointer; font-size: 16px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
    }
    #nomadas-chat-send:hover { background: #005f8e; }
    #nomadas-chat-send:disabled { background: #aaa; cursor: default; }
  `;
  document.head.appendChild(style);

  document.body.insertAdjacentHTML("beforeend", `
    <button id="nomadas-chat-btn" aria-label="Abrir chat">🏄</button>
    <div id="nomadas-chat-box" role="dialog" aria-label="Chat Nomadas Surf Park">
      <div id="nomadas-chat-header">
        <span class="dot"></span> Nomadas Surf Park
      </div>
      <div id="nomadas-chat-messages"></div>
      <div id="nomadas-chat-input-row">
        <textarea id="nomadas-chat-input" rows="1"
          placeholder="Escribe tu pregunta..." aria-label="Mensaje"></textarea>
        <button id="nomadas-chat-send" aria-label="Enviar">➤</button>
      </div>
    </div>
  `);

  const history = [];
  let sending = false;

  const btn     = document.getElementById("nomadas-chat-btn");
  const box     = document.getElementById("nomadas-chat-box");
  const msgs    = document.getElementById("nomadas-chat-messages");
  const input   = document.getElementById("nomadas-chat-input");
  const sendBtn = document.getElementById("nomadas-chat-send");

  function addMsg(text, role) {
    const div = document.createElement("div");
    div.className = `nc-msg ${role}`;
    div.textContent = text;
    msgs.appendChild(div);
    msgs.scrollTop = msgs.scrollHeight;
    return div;
  }

  btn.addEventListener("click", () => {
    const isOpen = box.classList.toggle("open");
    if (isOpen && msgs.children.length === 0) {
      addMsg("¡Hola! 🏄 Soy el asistente de Nomadas Surf Park.\n¿En qué puedo ayudarte? Puedo informarte sobre actividades, horarios y disponibilidad.", "bot");
    }
    if (isOpen) input.focus();
  });

  async function sendMessage() {
    const text = input.value.trim();
    if (!text || sending) return;
    sending = true;
    sendBtn.disabled = true;
    input.value = "";

    addMsg(text, "user");
    history.push({ role: "user", content: text });
    const typingEl = addMsg("Escribiendo…", "bot typing");

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      const reply = data.reply || "No pude obtener respuesta.";
      typingEl.remove();
      addMsg(reply, "bot");
      history.push({ role: "assistant", content: reply });
    } catch {
      typingEl.remove();
      addMsg("Error de conexión. Inténtalo de nuevo.", "bot typing");
      history.pop();
    }

    sending = false;
    sendBtn.disabled = false;
    input.focus();
  }

  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 80) + "px";
  });
})();
