// Chat de la barbería. Regla de seguridad: el texto del modelo SIEMPRE se pinta con
// textContent / createTextNode, nunca con innerHTML (así un <script> se ve como texto).
const $ = (s) => document.querySelector(s);
const ROL = document.body.dataset.rol || "interno"; // "cliente" en la web pública
const chat = $("#chat");
const entrada = $("#entrada");
const enviar = $("#enviar");

const NOMBRES = { crear_cita: "Crear cita", cancelar_cita: "Cancelar cita" };

function crear(etiqueta, clase, texto) {
  const el = document.createElement(etiqueta);
  if (clase) el.className = clase;
  if (texto !== undefined) el.textContent = texto;
  return el;
}

// Markdown mínimo y seguro: solo **negrita**, construida con nodos.
function conNegritas(el, texto) {
  texto.split("**").forEach((trozo, i) => {
    el.append(i % 2 ? crear("strong", "", trozo) : document.createTextNode(trozo));
  });
}

function mensaje(quien, texto, traza = []) {
  $(".bienvenida")?.remove();
  const div = crear("div", `msg ${quien}`);
  if (traza.length) {
    const t = crear("div", "traza");
    traza.forEach((linea) => t.append(crear("div", "", linea)));
    div.append(t);
  }
  if (texto) {
    const cuerpo = crear("div", "texto");
    conNegritas(cuerpo, texto);
    div.append(cuerpo);
  }
  chat.append(div);
  chat.scrollTop = chat.scrollHeight;
  return div;
}

function ocupado(si) {
  entrada.disabled = si;
  enviar.disabled = si;
  $("#pensando").hidden = !si;
}

async function api(ruta, datos) {
  const r = await fetch(ruta, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(datos),
  });
  try {
    return await r.json();
  } catch {
    return { tipo: "error", texto: `Error del servidor (${r.status})`, traza: [] };
  }
}

function mostrar(r) {
  if (r.tipo === "confirmar") return pedirConfirmacion(r);
  mensaje(r.tipo === "error" ? "error" : "bot", r.texto || "(sin respuesta)", r.traza || []);
  ocupado(false);
  entrada.focus();
}

function pedirConfirmacion(r) {
  $("#pensando").hidden = true; // el campo de texto sigue bloqueado hasta responder
  const div = mensaje("confirmar", "", r.traza || []);
  div.append(crear("p", "titulo", `⚠️ El asistente quiere: ${NOMBRES[r.tool] || r.tool}`));
  const lista = crear("dl", "argumentos");
  for (const [clave, valor] of Object.entries(r.argumentos || {})) {
    lista.append(crear("dt", "", clave), crear("dd", "", String(valor)));
  }
  div.append(lista);
  const botones = crear("div", "botones");
  const si = crear("button", "peligro", "Sí, hazlo");
  const no = crear("button", "secundario", "No");
  botones.append(si, no);
  div.append(botones);
  chat.scrollTop = chat.scrollHeight;

  const responder = async (respuesta) => {
    si.disabled = no.disabled = true;
    botones.replaceWith(crear("p", "decision", respuesta ? "✔ Confirmado" : "✋ Rechazado"));
    $("#pensando").hidden = false;
    mostrar(await api(`/api/${ROL}/confirmar`, { si: respuesta }));
  };
  si.addEventListener("click", () => responder(true));
  no.addEventListener("click", () => responder(false));
}

async function preguntar(texto) {
  mensaje("yo", texto);
  ocupado(true);
  mostrar(await api(`/api/${ROL}/chat`, { texto }));
}

$("#formulario").addEventListener("submit", (e) => {
  e.preventDefault();
  const texto = entrada.value.trim();
  if (!texto) return;
  entrada.value = "";
  preguntar(texto);
});

document.querySelectorAll(".chip").forEach((chip) =>
  chip.addEventListener("click", () => preguntar(chip.textContent))
);

$("#reiniciar").addEventListener("click", async () => {
  await api(`/api/${ROL}/reiniciar`, {});
  location.reload();
});

fetch("/api/info")
  .then((r) => r.json())
  .then((d) => {
    if ($("#modelo")) $("#modelo").textContent = d.modelo;
    if (ROL === "interno") {
      $("#barberia").textContent = d.barberia;
      document.title = `${d.barberia} · Panel interno`;
    }
  });

if (ROL === "interno") entrada.focus();
