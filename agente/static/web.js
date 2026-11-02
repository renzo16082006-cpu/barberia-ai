// Web pública de El Navajas:
// - Horario leído de la base de datos (/api/horario, tabla horarios): "Abierto ahora", tabla con el
//   día de hoy marcado y validación del cupón. El horario escrito en el HTML es solo el respaldo sin JS.
// - Cupón de reserva: prepara el mensaje y abre WhatsApp (sin guardar nada en ningún servidor).
// - Entradas suaves de cada sección al aparecer.
document.documentElement.classList.add("js");

(() => {
  // Se rellena con /api/horario. Clave = día de JavaScript (0 = domingo ... 6 = sábado); null = cerrado.
  // Ejemplo: { 1: ["10:00", "20:00"], ..., 6: ["09:00", "14:00"], 0: null }
  let HORARIO = null;
  const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  const TELEFONO = "34977000111";

  const partes = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Madrid", weekday: "short", hour: "numeric", minute: "numeric", hourCycle: "h23",
  }).formatToParts(new Date());
  const valor = (t) => partes.find((p) => p.type === t).value;
  const dia = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(valor("weekday"));
  const ahora = Number(valor("hour")) * 60 + Number(valor("minute")); // minutos desde medianoche
  const minutos = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h * 60 + m; };
  const corta = (hhmm) => hhmm.replace(/^0/, ""); // "09:00" -> "9:00"

  document.querySelectorAll("[data-dias]").forEach((fila) => {
    if (fila.dataset.dias.split(",").map(Number).includes(dia)) fila.classList.add("hoy");
  });

  function pintarEstado() {
    const texto = document.getElementById("estado-texto");
    const hoy = HORARIO[dia];
    if (hoy && ahora >= minutos(hoy[0]) && ahora < minutos(hoy[1])) {
      document.getElementById("estado").classList.add("abierto");
      texto.textContent = `Abierto ahora, hasta las ${corta(hoy[1])}`;
    } else if (hoy && ahora < minutos(hoy[0])) {
      texto.textContent = `Abrimos hoy a las ${corta(hoy[0])}`;
    } else {
      for (let i = 1; i <= 7; i++) {
        const d = (dia + i) % 7;
        if (HORARIO[d]) {
          texto.textContent = `Abrimos ${i === 1 ? "mañana" : "el " + DIAS[d]} a las ${corta(HORARIO[d][0])}`;
          break;
        }
      }
    }
  }

  // Tabla corta: agrupa días seguidos con el mismo horario ("Lunes a viernes") y junta los cerrados al final.
  function pintarTabla() {
    const NOMBRES = ["Domingo", "Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado"];
    const fila = (dias, dt, dd) => {
      const div = document.createElement("div");
      div.dataset.dias = dias.join(",");
      if (dias.includes(dia)) div.classList.add("hoy");
      const t = document.createElement("dt");
      t.textContent = dt;
      const d = document.createElement("dd");
      d.textContent = dd;
      div.append(t, d);
      return div;
    };
    const filas = [];
    const cerrados = [];
    let grupo = [];
    const cerrarGrupo = () => {
      if (!grupo.length) return;
      const [a, b] = HORARIO[grupo[0]];
      const nombre = grupo.length === 1 ? NOMBRES[grupo[0]]
        : `${NOMBRES[grupo[0]]} a ${NOMBRES[grupo.at(-1)].toLowerCase()}`;
      filas.push(fila(grupo, nombre, `${corta(a)} – ${corta(b)}`));
      grupo = [];
    };
    for (const d of [1, 2, 3, 4, 5, 6, 0]) { // de lunes a domingo
      const h = HORARIO[d];
      if (!h) { cerrarGrupo(); cerrados.push(d); continue; }
      if (grupo.length && HORARIO[grupo[0]].join() !== h.join()) cerrarGrupo();
      grupo.push(d);
    }
    cerrarGrupo();
    if (cerrados.length) {
      const nombres = cerrados.map((d, i) => (i ? NOMBRES[d].toLowerCase() : NOMBRES[d]));
      const lista = nombres.length > 1 ? `${nombres.slice(0, -1).join(", ")} y ${nombres.at(-1)}` : nombres[0];
      filas.push(fila(cerrados, lista, "Cerrado"));
    }
    document.querySelector(".horario-corto").replaceChildren(...filas);
  }

  fetch("/api/horario")
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((datos) => {
      HORARIO = {};
      for (let d = 0; d < 7; d++) HORARIO[d] = datos.horario[String(d === 0 ? 7 : d)] || null; // ISO 7 = domingo
      pintarEstado();
      pintarTabla();
    })
    .catch(() => {}); // sin horario: se queda el texto del HTML

  // Cupón de reserva → WhatsApp
  const cupon = document.getElementById("cupon");
  const campoDia = document.getElementById("c-dia");
  const iso = (f) => f.toLocaleDateString("sv-SE", { timeZone: "Europe/Madrid" }); // AAAA-MM-DD
  campoDia.min = iso(new Date());
  // Vista previa: el mensaje de WhatsApp se escribe mientras rellenas el cupón
  const vista = document.getElementById("vista-texto");
  const componer = () => {
    const d = new FormData(cupon);
    const nombre = (d.get("nombre") || "").trim();
    let cuando = "";
    if (d.get("dia")) {
      const f = new Date(`${d.get("dia")}T12:00:00`);
      cuando = ` el ${f.toLocaleDateString("es-ES", { weekday: "long", day: "numeric", month: "long" })}`;
    }
    return `Hola${nombre ? `, soy ${nombre}` : ""}. Quiero pedir cita para ${d.get("servicio")}${cuando}, ${d.get("hora")}. ¿Qué hora tenéis libre?`;
  };
  const actualizar = () => { vista.textContent = componer(); };
  cupon.addEventListener("input", actualizar);
  cupon.addEventListener("change", actualizar);
  actualizar();

  cupon.addEventListener("submit", (e) => {
    e.preventDefault();
    const datos = new FormData(cupon);
    const elegido = new Date(`${datos.get("dia")}T12:00:00`);
    const aviso = document.getElementById("cupon-aviso");
    if (HORARIO && !HORARIO[elegido.getDay()]) {
      aviso.textContent = "Ese día está cerrado. Mira el horario y elige otro.";
      campoDia.focus();
      return;
    }
    aviso.textContent = "";
    const mensaje = componer();
    window.open(`https://wa.me/${TELEFONO}?text=${encodeURIComponent(mensaje)}`, "_blank", "noopener");
  });

  // Asistente flotante: se abre desde el botón, se cierra con ✕ o Esc, y el foco va y vuelve.
  const panel = document.getElementById("asistente");
  const abrir = document.getElementById("abrir-chat");
  const cerrar = document.getElementById("cerrar-chat");
  const ponerChat = (abierto) => {
    panel.classList.toggle("abierto", abierto);
    panel.inert = !abierto;
    abrir.setAttribute("aria-expanded", String(abierto));
    (abierto ? document.getElementById("entrada") : abrir).focus();
  };
  abrir.addEventListener("click", () => ponerChat(true));
  cerrar.addEventListener("click", () => ponerChat(false));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && panel.classList.contains("abierto")) ponerChat(false);
  });

  // Menú fijo: se oscurece al bajar
  const menu = document.getElementById("menu-fijo");
  const alBajar = () => menu.classList.toggle("con-fondo", window.scrollY > 40);
  window.addEventListener("scroll", alBajar, { passive: true });
  alBajar();

  // Entradas al hacer scroll (una vez por sección)
  const observador = new IntersectionObserver((entradas) => {
    entradas.forEach((en) => {
      if (en.isIntersecting) {
        en.target.classList.add("visible");
        observador.unobserve(en.target);
      }
    });
  }, { rootMargin: "0px 0px -10% 0px" });
  document.querySelectorAll(".aparece, .revela").forEach((el) => observador.observe(el));
})();
