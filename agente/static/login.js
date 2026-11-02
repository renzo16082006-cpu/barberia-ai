// Acceso del personal. La contraseña viaja solo en el cuerpo de un POST JSON a /api/login
// (nunca en la URL, que acaba en el historial). Si es correcta, el servidor pone la cookie de
// sesión (HttpOnly: este JavaScript ni siquiera puede leerla) y se pasa al panel.
const formulario = document.getElementById("acceso");
const campo = document.getElementById("clave");
const boton = document.getElementById("entrar");
const aviso = document.getElementById("aviso");

formulario.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (!campo.value) {
    aviso.textContent = "Escribe la contraseña.";
    campo.focus();
    return;
  }
  boton.disabled = true;
  aviso.textContent = "";
  try {
    const r = await fetch("/api/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ clave: campo.value }),
    });
    if (r.ok) {
      location.replace("/panel"); // replace: "Atrás" no vuelve a esta pantalla
      return;
    }
    const datos = await r.json().catch(() => ({}));
    aviso.textContent = datos.texto || "No se ha podido entrar.";
  } catch {
    aviso.textContent = "No hay conexión con el servidor.";
  }
  campo.value = ""; // no dejar la contraseña escrita
  campo.focus();
  boton.disabled = false;
});
