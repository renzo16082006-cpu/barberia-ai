// Web pública de El Navajas:
// - "Abierto ahora" con la hora de Tarragona, y el poste solo gira si está abierto (como uno de verdad).
// - Día de hoy marcado en el horario.
// - Cupón de reserva: prepara el mensaje y abre WhatsApp (sin guardar nada en ningún servidor).
// - Entradas suaves de cada sección al aparecer.
document.documentElement.classList.add("js");

(() => {
  const HORARIO = { 1: [10, 20], 2: [10, 20], 3: [10, 20], 4: [10, 20], 5: [10, 20], 6: [9, 14], 0: null };
  const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
  const TELEFONO = "34977000111";

  const partes = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Madrid", weekday: "short", hour: "numeric", minute: "numeric", hourCycle: "h23",
  }).formatToParts(new Date());
  const valor = (t) => partes.find((p) => p.type === t).value;
  const dia = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].indexOf(valor("weekday"));
  const hora = Number(valor("hour")) + Number(valor("minute")) / 60;

  document.querySelectorAll("[data-dias]").forEach((fila) => {
    if (fila.dataset.dias.split(",").map(Number).includes(dia)) fila.classList.add("hoy");
  });

  const texto = document.getElementById("estado-texto");
  const hoy = HORARIO[dia];
  if (hoy && hora >= hoy[0] && hora < hoy[1]) {
    document.getElementById("estado").classList.add("abierto");
    texto.textContent = `Abierto ahora, hasta las ${hoy[1]}:00`;
  } else if (hoy && hora < hoy[0]) {
    texto.textContent = `Abrimos hoy a las ${hoy[0]}:00`;
  } else {
    for (let i = 1; i <= 7; i++) {
      const d = (dia + i) % 7;
      if (HORARIO[d]) {
        texto.textContent = `Abrimos ${i === 1 ? "mañana" : "el " + DIAS[d]} a las ${HORARIO[d][0]}:00`;
        break;
      }
    }
  }

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
    if (!HORARIO[elegido.getDay()]) {
      aviso.textContent = "Ese día está cerrado. Elige de lunes a sábado.";
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
