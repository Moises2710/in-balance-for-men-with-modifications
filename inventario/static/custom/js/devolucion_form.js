// JavaScript para el formulario de devoluciones
document.addEventListener("DOMContentLoaded", function () {
  // Obtener el valor del total pagado desde el template
  const totalPagado = parseFloat(
    document.getElementById("total-pagado-hidden").value
  );

  function calcularTotal() {
    let totalBuenEstado = 0;
    let totalDanados = 0;
    let totalDevolucion = 0;
    let hayProductos = false;

    // Calcular totales
    document.querySelectorAll(".cantidad-input").forEach((input) => {
      const cantidad = parseInt(input.value) || 0;
      // Convertir coma decimal a punto para JavaScript
      const precioRaw = input.dataset.precio.replace(",", ".");
      const precio = parseFloat(precioRaw);
      // Usar Math.round para evitar errores de precisión flotante
      const subtotal = Math.round(cantidad * precio * 100) / 100;

      if (cantidad > 0) {
        hayProductos = true;
      }

      if (input.name.includes("cantidad_devuelta_")) {
        totalBuenEstado += subtotal;
      } else if (input.name.includes("cantidad_danada_")) {
        totalDanados += subtotal;
      }
    });

    totalDevolucion = totalBuenEstado + totalDanados;

    // Actualizar la interfaz
    document.getElementById("totalBuenEstado").textContent =
      "$" + totalBuenEstado.toFixed(2);
    document.getElementById("totalDanados").textContent =
      "$" + totalDanados.toFixed(2);
    document.getElementById("totalDevolucion").textContent =
      "$" + totalDevolucion.toFixed(2);

    // Habilitar/deshabilitar botón
    const btnCrear = document.getElementById("btnCrearDevolucion");
    if (hayProductos) {
      btnCrear.disabled = false;
      btnCrear.classList.remove("btn-secondary");
      btnCrear.classList.add("btn-primary");
    } else {
      btnCrear.disabled = true;
      btnCrear.classList.remove("btn-primary");
      btnCrear.classList.add("btn-secondary");
    }

    // Validar reembolso
    const reembolsado =
      parseFloat(document.getElementById("reembolsado").value) || 0;
    const maxReembolso = Math.min(totalDevolucion, totalPagado);

    if (reembolsado > maxReembolso) {
      document
        .getElementById("reembolsado")
        .setCustomValidity(
          `El reembolso no puede ser mayor a $${maxReembolso.toFixed(2)}`
        );
    } else {
      document.getElementById("reembolsado").setCustomValidity("");
    }
  }

  // Validar inputs de cantidad
  document.querySelectorAll(".cantidad-input").forEach((input) => {
    input.addEventListener("input", function () {
      const max = parseInt(this.max);
      const value = parseInt(this.value);

      if (value > max) {
        this.value = max;
      }

      // Validar que la suma de devuelta + dañada no exceda lo disponible
      const detalleId = this.dataset.detalleId;
      const devueltaInput = document.getElementById(
        `cantidad_devuelta_${detalleId}`
      );
      const danadaInput = document.getElementById(
        `cantidad_danada_${detalleId}`
      );

      const devuelta = parseInt(devueltaInput.value) || 0;
      const danada = parseInt(danadaInput.value) || 0;
      const disponible = parseInt(devueltaInput.max);

      if (devuelta + danada > disponible) {
        if (this === devueltaInput) {
          danadaInput.value = Math.max(0, disponible - devuelta);
        } else {
          devueltaInput.value = Math.max(0, disponible - danada);
        }
      }

      calcularTotal();
    });
  });

  // Validar reembolso
  document
    .getElementById("reembolsado")
    .addEventListener("input", calcularTotal);

  // Validar formulario antes de enviar
  document
    .getElementById("devolucionForm")
    .addEventListener("submit", function (e) {
      const totalDevolucion = parseFloat(
        document.getElementById("totalDevolucion").textContent.replace("$", "")
      );
      const reembolsado =
        parseFloat(document.getElementById("reembolsado").value) || 0;

      if (totalDevolucion === 0) {
        e.preventDefault();
        alert("Debe seleccionar al menos un producto para devolver");
        return false;
      }

      if (reembolsado > totalDevolucion) {
        e.preventDefault();
        alert(
          "El monto reembolsado no puede ser mayor al total de la devolución"
        );
        return false;
      }

      if (reembolsado > totalPagado) {
        e.preventDefault();
        alert(
          "El monto reembolsado no puede ser mayor al total pagado de la venta"
        );
        return false;
      }
    });
});
