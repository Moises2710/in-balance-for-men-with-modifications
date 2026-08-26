$(document).ready(function () {
  // Variables globales
  let productos = [];
  let clientes = [];
  let vendedores = [];
  let metodosPago = [];
  let monedas = [];
  let productosVenta = [];
  let pagosVenta = [];
  let productosSeleccionados = new Set(); // Para tracking de productos seleccionados
  let ventaEnProceso = false; // Variable para prevenir múltiples envíos

  // Inicializar la aplicación
  initVentaApp();

  function initVentaApp() {
    // Cargar datos iniciales
    cargarDatosIniciales();

    // Configurar eventos
    configurarEventos();

    // Configurar fecha actual
    configurarFechaActual();
  }

  function cargarDatosIniciales() {
    $.ajax({
      url: "/venta/ajax/datos-venta/",
      method: "GET",
      success: function (response) {
        if (response.success) {
          productos = response.productos;
          clientes = response.clientes;
          vendedores = response.vendedores;
          metodosPago = response.metodos_pago;
          monedas = response.monedas;

          // Llenar selectores
          llenarSelectCliente();
          llenarSelectVendedor();
          llenarSelectFiltros();

          console.log("Datos cargados exitosamente");
        } else {
          mostrarError("Error al cargar datos: " + response.error);
        }
      },
      error: function (xhr, status, error) {
        mostrarError("Error de conexión al cargar datos");
        console.error("Error:", error);
      },
    });
  }

  function configurarEventos() {
    // Eventos para búsqueda rápida
    $("#btn-agregar-rapido").on("click", agregarProductoPorCodigo);
    $("#busqueda-rapida").on("keyup", function (e) {
      if (e.keyCode === 13) {
        // Enter
        agregarProductoPorCodigo();
      }
    });

    // Evento para limpiar productos - ahora usa modal
    $("#limpiar-productos").on("click", function () {
      if ($("#productos-body tr").length === 0) {
        mostrarToast("No hay productos para limpiar", "warning");
        return;
      }
      $("#modalConfirmarLimpiar").modal("show");
    });

    // Confirmar limpiar tabla
    $("#confirmarLimpiarTabla").on("click", function () {
      $("#productos-body").empty();
      productosSeleccionados.clear();
      calcularTotales();
      $("#modalConfirmarLimpiar").modal("hide");
      mostrarToast("Productos eliminados correctamente", "success");
      // Actualizar estado de productos en modal si está abierto
      if ($("#modalProductos").hasClass("show")) {
        actualizarEstadoProductosModal();
      }
    });

    // Eventos para productos
    $("#add-producto").on("click", abrirModalProductos);
    $(document).on("click", ".remove-producto", eliminarFilaProducto);
    $(document).on(
      "input",
      ".cantidad, .precio-unitario",
      calcularSubtotalFila
    );

    // Eventos para pagos
    $("#add-pago").on("click", agregarFilaPago);
    $(document).on("click", ".remove-pago", eliminarFilaPago);
    $(document).on("change", ".metodo-pago", onMetodoPagoChange);
    $(document).on(
      "input",
      ".monto-pagado, .tasa-cambio",
      calcularPagoConvertido
    );

    // Eventos para cálculos generales con validación de descuento
    $("#descuento").on("input", function () {
      validarDescuento();
      calcularTotales();
    });
    $("#comision_porcentaje").on("input", calcularTotales);

    // Evento para cambio de cliente - actualizar saldo en pagos existentes
    $("#cliente").on("change", function () {
      actualizarSaldoEnPagos();
    });

    // Eventos para filtros del modal
    $("#btnFiltrar").on("click", filtrarProductos);
    $("#filtroCodigo, #filtroPrecioMin, #filtroPrecioMax").on(
      "keyup",
      function (e) {
        if (e.keyCode === 13) {
          // Enter
          filtrarProductos();
        }
      }
    );

    // Evento para enviar formulario
    $("#venta-form").on("submit", enviarVenta);
  }

  function configurarFechaActual() {
    const now = new Date();
    // Ajustar por zona horaria local
    const offset = now.getTimezoneOffset();
    const localDate = new Date(now.getTime() - offset * 60 * 1000);
    const fechaActual = localDate.toISOString().slice(0, 16);
    $("#fecha").val(fechaActual);
  }

  // ========================================
  // FUNCIONES PARA BÚSQUEDA RÁPIDA
  // ========================================

  function agregarProductoPorCodigo() {
    const codigo = $("#busqueda-rapida").val().trim();
    if (!codigo) {
      mostrarToast("Ingrese un código de producto", "warning");
      return;
    }

    const producto = productos.find(
      (p) => p.codigo.toLowerCase() === codigo.toLowerCase()
    );
    if (!producto) {
      mostrarToast("No se encontró un producto con ese código", "warning");
      return;
    }

    if (producto.stock <= 0) {
      mostrarToast("Este producto no tiene stock disponible", "warning");
      return;
    }

    agregarProductoDesdeModal(producto);
    $("#busqueda-rapida").val("").focus();
  }

  // ========================================
  // FUNCIONES PARA EL MODAL DE PRODUCTOS
  // ========================================

  function abrirModalProductos() {
    // Cargar productos en el modal
    cargarProductosEnModal();
  }

  function cargarProductosEnModal() {
    const tbody = $("#listaProductos");
    tbody.empty();

    productos.forEach(function (producto) {
      const yaSeleccionado = productosSeleccionados.has(producto.id);
      const sinStock = producto.stock <= 0;
      const fila = `
                <tr class="producto-item ${
                  yaSeleccionado ? "producto-seleccionado" : ""
                }" data-producto='${JSON.stringify(producto)}'>
                    <td>${producto.codigo}</td>
                    <td>${producto.marca}</td>
                    <td>${producto.tipo}</td>
                    <td>${producto.color}</td>
                    <td>${producto.talla}</td>
                    <td><span class="badge bg-${
                      producto.stock > 0 ? "success" : "danger"
                    }">${producto.stock}</span></td>
                    <td>$${producto.precio_venta}</td>
                    <td>
                        <button type="button" class="btn btn-sm ${
                          yaSeleccionado
                            ? "btn-producto-seleccionado"
                            : "btn-primary"
                        } seleccionar-producto" 
                                ${sinStock || yaSeleccionado ? "disabled" : ""}>
                            ${yaSeleccionado ? "Seleccionado" : "Seleccionar"}
                        </button>
                    </td>
                </tr>
            `;
      tbody.append(fila);
    });

    // Evento para seleccionar producto
    $(".seleccionar-producto").on("click", function () {
      const fila = $(this).closest("tr");
      const productoData = fila.data("producto");
      agregarProductoDesdeModal(productoData);
    });
  }

  function actualizarEstadoProductosModal() {
    $("#listaProductos tr").each(function () {
      const producto = $(this).data("producto");
      const yaSeleccionado = productosSeleccionados.has(producto.id);
      const boton = $(this).find(".seleccionar-producto");
      const fila = $(this);

      if (yaSeleccionado) {
        fila.addClass("producto-seleccionado");
        boton
          .removeClass("btn-primary")
          .addClass("btn-producto-seleccionado")
          .prop("disabled", true)
          .text("Seleccionado");
      } else {
        fila.removeClass("producto-seleccionado");
        boton
          .removeClass("btn-producto-seleccionado")
          .addClass("btn-primary")
          .prop("disabled", producto.stock <= 0)
          .text("Seleccionar");
      }
    });
  }

  function agregarProductoDesdeModal(producto) {
    // Verificar si el producto ya está en la venta
    if (productosSeleccionados.has(producto.id)) {
      mostrarToast("Este producto ya está agregado a la venta", "warning");
      return;
    }

    // Agregar fila de producto
    const filaHtml = `
            <tr class="fila-producto" data-producto-id="${producto.id}">
                <td>
                    <strong>${producto.codigo}</strong>
                </td>
                <td>${producto.tipo}</td>
                <td>${producto.marca}</td>
                <td>${producto.talla}</td>
                <td>
                    <input type="number" class="form-control cantidad" 
                           min="1" max="${producto.stock}" step="1" value="1" required>
                </td>
                <td>
                    <input type="number" class="form-control precio-unitario" 
                           step="0.01" min="0" value="${producto.precio_venta}" required>
                </td>
                <td>
                    <input type="text" class="form-control subtotal-fila" readonly>
                </td>
                <td>
                    <button type="button" class="btn btn-sm btn-danger remove-producto">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
                        <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6Z"/>
                        <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1ZM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118ZM2.5 3h11V2h-11v1Z"/>
                      </svg>
                    </button>
                </td>
            </tr>
        `;

    $("#productos-body").append(filaHtml);

    // Marcar producto como seleccionado
    productosSeleccionados.add(producto.id);

    // Calcular subtotal de la nueva fila
    const nuevaFila = $("#productos-body tr:last");
    calcularSubtotalFila.call(nuevaFila);

    // NO cerrar modal - mantener abierto para más selecciones
    // Actualizar estado visual del producto en el modal
    actualizarEstadoProductosModal();

    // Mostrar mensaje de éxito con toast
    mostrarToast(
      `Producto "${producto.codigo}" agregado correctamente`,
      "success"
    );
  }

  function filtrarProductos() {
    const codigo = $("#filtroCodigo").val().toLowerCase();
    const marca = $("#filtroMarca").val();
    const tipo = $("#filtroTipo").val();
    const talla = $("#filtroTalla").val();
    const precioMin = parseFloat($("#filtroPrecioMin").val()) || 0;
    const precioMax = parseFloat($("#filtroPrecioMax").val()) || 999999;

    const tbody = $("#listaProductos");
    tbody.empty();

    const productosFiltrados = productos.filter(function (producto) {
      const cumpleCodigo =
        !codigo || producto.codigo.toLowerCase().includes(codigo);
      const cumpleMarca = !marca || producto.marca === marca;
      const cumpleTipo = !tipo || producto.tipo === tipo;
      const cumpleTalla = !talla || producto.talla === talla;
      const precio = parseFloat(producto.precio_venta);
      const cumplePrecio = precio >= precioMin && precio <= precioMax;

      return (
        cumpleCodigo && cumpleMarca && cumpleTipo && cumpleTalla && cumplePrecio
      );
    });

    if (productosFiltrados.length === 0) {
      tbody.append(`
                <tr>
                    <td colspan="8" class="text-center text-muted">
                      No se encontraron productos con los filtros aplicados
                    </td>
                </tr>
            `);
      return;
    }

    productosFiltrados.forEach(function (producto) {
      const yaSeleccionado = productosSeleccionados.has(producto.id);
      const sinStock = producto.stock <= 0;
      const fila = `
                <tr class="producto-item ${
                  yaSeleccionado ? "producto-seleccionado" : ""
                }" data-producto='${JSON.stringify(producto)}'>
                    <td>${producto.codigo}</td>
                    <td>${producto.marca}</td>
                    <td>${producto.tipo}</td>
                    <td>${producto.color}</td>
                    <td>${producto.talla}</td>
                    <td><span class="badge bg-${
                      producto.stock > 0 ? "success" : "danger"
                    }">${producto.stock}</span></td>
                    <td>$${producto.precio_venta}</td>
                    <td>
                        <button type="button" class="btn btn-sm ${
                          yaSeleccionado
                            ? "btn-producto-seleccionado"
                            : "btn-primary"
                        } seleccionar-producto" 
                                ${sinStock || yaSeleccionado ? "disabled" : ""}>
                            ${yaSeleccionado ? "Seleccionado" : "Seleccionar"}
                        </button>
                    </td>
                </tr>
            `;
      tbody.append(fila);
    });

    // Re-asignar eventos
    $(".seleccionar-producto").on("click", function () {
      const fila = $(this).closest("tr");
      const productoData = fila.data("producto");
      agregarProductoDesdeModal(productoData);
    });
  }

  // ========================================
  // FUNCIONES PARA PRODUCTOS
  // ========================================

  function eliminarFilaProducto() {
    const fila = $(this).closest(".fila-producto");
    const productoId = fila.data("producto-id");

    // Remover de productos seleccionados
    productosSeleccionados.delete(productoId);

    fila.remove();
    calcularTotales();

    // Actualizar modal si está abierto
    if ($("#modalProductos").hasClass("show")) {
      actualizarEstadoProductosModal();
    }
  }

  function calcularSubtotalFila() {
    const fila = $(this).closest(".fila-producto");
    const precio = parseFloat(fila.find(".precio-unitario").val()) || 0;
    const cantidad = parseInt(fila.find(".cantidad").val()) || 0;
    const subtotal = precio * cantidad;

    fila.find(".subtotal-fila").val(subtotal.toFixed(2));
    calcularTotales();
  }

  // ========================================
  // FUNCIONES PARA PAGOS CON VALIDACIONES DINÁMICAS
  // ========================================

  function agregarFilaPago() {
    const filaHtml = `
            <div class="pago-item">
                <div class="row g-2">
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">Monto</label>
                        <input type="number" class="form-control monto-pagado" step="0.01" min="0" required>
                        <div class="invalid-feedback"></div>
                    </div>
                    <div class="col-md-6">
                        <label class="form-label small fw-bold">Método</label>
                        <select class="form-select metodo-pago" required>
                            <option value="">Seleccione método</option>
                            ${metodosPago
                              .map(
                                (m) => `
                                <option value="${m.id}" data-moneda="${
                                  m.moneda
                                }" data-requiere-tasa="${
                                  m.requiere_tasa
                                }" data-es-saldo="${m.nombre === "Saldo"}">${
                                  m.nombre
                                }</option>
                            `
                              )
                              .join("")}
                        </select>
                        <div class="saldo-info mt-1" style="display: none;">
                            <small class="text-muted">Saldo disponible: <span class="saldo-disponible fw-bold text-success">$0.00</span></small>
                        </div>
                        <div class="invalid-feedback"></div>
                    </div>
                    <div class="col-md-12 tasa-cambio-container" style="display: none;">
                        <label class="form-label small fw-bold">Tasa de cambio (1 USD = ?)</label>
                        <input type="number" class="form-control tasa-cambio" step="0.01" min="0" placeholder="Ej: 36.50">
                        <div class="invalid-feedback"></div>
                    </div>
                    <div class="col-md-12">
                        <small class="text-muted">Equivalente en USD: <span class="equivalente-usd">$0.00</span></small>
                    </div>
                </div>
                <div class="d-flex justify-content-end mt-2">
                    <button type="button" class="btn btn-sm btn-danger remove-pago">
                      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-trash" viewBox="0 0 16 16">
                        <path d="M5.5 5.5A.5.5 0 0 1 6 6v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm2.5 0a.5.5 0 0 1 .5.5v6a.5.5 0 0 1-1 0V6a.5.5 0 0 1 .5-.5Zm3 .5a.5.5 0 0 0-1 0v6a.5.5 0 0 0 1 0V6Z"/>
                        <path d="M14.5 3a1 1 0 0 1-1 1H13v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V4h-.5a1 1 0 0 1-1-1V2a1 1 0 0 1 1-1H6a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1h3.5a1 1 0 0 1 1 1v1ZM4.118 4 4 4.059V13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1V4.059L11.882 4H4.118ZM2.5 3h11V2h-11v1Z"/>
                      </svg>
                    </button>
                </div>
            </div>
        `;

    $("#pagos-container").append(filaHtml);

    // Añadir validación en tiempo real al nuevo pago
    const nuevoPago = $("#pagos-container .pago-item:last");
    validarPagoDinamicamente(nuevoPago);
  }

  function validarPagoDinamicamente(pagoItem) {
    const montoPagado = pagoItem.find(".monto-pagado");
    const metodoPago = pagoItem.find(".metodo-pago");
    const tasaCambio = pagoItem.find(".tasa-cambio");

    // Validar monto
    montoPagado.on("input blur", function () {
      const monto = parseFloat($(this).val()) || 0;
      const total = parseFloat($("#total").text().replace("$", "")) || 0;
      const totalPagado = calcularTotalPagado();
      const faltante = total - totalPagado + monto; // Incluir este pago
      const metodoSeleccionado = pagoItem.find(".metodo-pago");
      const esSaldo = metodoSeleccionado
        .find("option:selected")
        .data("es-saldo");

      if (monto <= 0) {
        $(this).addClass("is-invalid");
        $(this)
          .siblings(".invalid-feedback")
          .text("El monto debe ser mayor a 0");
      } else if (esSaldo) {
        // Validaciones específicas para saldo del cliente
        const clienteId = $("#cliente").val();
        if (clienteId) {
          const cliente = clientes.find((c) => c.id == clienteId);
          if (cliente) {
            const saldoDisponible = parseFloat(cliente.saldo);
            if (saldoDisponible <= 0) {
              $(this).addClass("is-invalid");
              $(this)
                .siblings(".invalid-feedback")
                .text("El cliente no tiene saldo disponible");
            } else if (monto > saldoDisponible) {
              $(this).addClass("is-invalid");
              $(this)
                .siblings(".invalid-feedback")
                .text(
                  `Excede el saldo disponible ($${saldoDisponible.toFixed(2)})`
                );
            } else {
              $(this).removeClass("is-invalid");
              $(this).siblings(".invalid-feedback").text("");
            }
          }
        } else {
          $(this).addClass("is-invalid");
          $(this)
            .siblings(".invalid-feedback")
            .text("Debe seleccionar un cliente primero");
        }
      } else if (monto > faltante && faltante > 0) {
        $(this).addClass("is-invalid");
        $(this)
          .siblings(".invalid-feedback")
          .text(`Este pago excede el faltante ($${faltante.toFixed(2)})`);
      } else {
        $(this).removeClass("is-invalid");
        $(this).siblings(".invalid-feedback").text("");
      }

      calcularEquivalenteUSD(pagoItem);
    });

    // Validar método de pago
    metodoPago.on("change", function () {
      if (!$(this).val()) {
        $(this).addClass("is-invalid");
        $(this)
          .siblings(".invalid-feedback")
          .text("Debe seleccionar un método de pago");
      } else {
        $(this).removeClass("is-invalid");
        $(this).siblings(".invalid-feedback").text("");
      }
    });

    // Validar tasa de cambio
    tasaCambio.on("input blur", function () {
      const tasa = parseFloat($(this).val()) || 0;
      const container = $(this).closest(".tasa-cambio-container");

      if (container.is(":visible") && tasa <= 0) {
        $(this).addClass("is-invalid");
        $(this)
          .siblings(".invalid-feedback")
          .text("Debe proporcionar una tasa válida");
      } else {
        $(this).removeClass("is-invalid");
        $(this).siblings(".invalid-feedback").text("");
      }

      calcularEquivalenteUSD(pagoItem);
    });
  }

  function calcularEquivalenteUSD(pagoItem) {
    const monto = parseFloat(pagoItem.find(".monto-pagado").val()) || 0;
    const tasa = parseFloat(pagoItem.find(".tasa-cambio").val()) || 1;
    const metodoId = pagoItem.find(".metodo-pago").val();

    let equivalenteUSD = 0;
    if (metodoId && monto > 0) {
      const metodo = metodosPago.find((m) => m.id == metodoId);
      if (metodo && metodo.requiere_tasa && tasa > 0) {
        equivalenteUSD = monto / tasa;
      } else {
        equivalenteUSD = monto;
      }
    }

    pagoItem.find(".equivalente-usd").text(`$${equivalenteUSD.toFixed(2)}`);
  }

  function calcularTotalPagado() {
    let totalPagado = 0;
    $(".pago-item").each(function () {
      const monto = parseFloat($(this).find(".monto-pagado").val()) || 0;
      const tasa = parseFloat($(this).find(".tasa-cambio").val()) || 1;
      const metodoId = $(this).find(".metodo-pago").val();

      if (metodoId && monto > 0) {
        const metodo = metodosPago.find((m) => m.id == metodoId);
        if (metodo && metodo.moneda !== "USD" && tasa > 0) {
          totalPagado += monto / tasa;
        } else {
          totalPagado += monto;
        }
      }
    });
    return totalPagado;
  }

  function calcularFaltantePorPagar() {
    const subtotal = calcularSubtotalProductos();
    const descuento = parseFloat($("#descuento").val()) || 0;
    const total = Math.max(0, subtotal - descuento);
    const totalPagado = calcularTotalPagado();
    return Math.max(0, total - totalPagado);
  }

  function eliminarFilaPago() {
    $(this).closest(".pago-item").remove();
    calcularTotales();
  }

  function onMetodoPagoChange() {
    const select = $(this);
    const pagoItem = select.closest(".pago-item");
    const tasaContainer = pagoItem.find(".tasa-cambio-container");
    const saldoInfo = pagoItem.find(".saldo-info");
    const montoInput = pagoItem.find(".monto-pagado");
    const metodoId = select.val();

    // Ocultar información de saldo por defecto
    saldoInfo.hide();

    if (metodoId) {
      const metodo = metodosPago.find((m) => m.id == metodoId);

      // Manejar tasa de cambio
      if (metodo && metodo.requiere_tasa) {
        tasaContainer.show();
      } else {
        tasaContainer.hide();
      }

      // Manejar saldo del cliente
      const esSaldo = select.find("option:selected").data("es-saldo");
      if (esSaldo) {
        const clienteId = $("#cliente").val();
        if (clienteId) {
          const cliente = clientes.find((c) => c.id == clienteId);
          if (cliente) {
            const saldoDisponible = parseFloat(cliente.saldo);
            const saldoSpan = saldoInfo.find(".saldo-disponible");
            saldoSpan.text(`$${saldoDisponible.toFixed(2)}`);

            // Aplicar color según el saldo
            saldoSpan.removeClass("text-success text-danger");
            if (saldoDisponible < 0) {
              saldoSpan.addClass("text-danger");
            } else {
              saldoSpan.addClass("text-success");
            }

            saldoInfo.show();

            // Configurar el input para saldo
            if (saldoDisponible > 0) {
              // Permitir usar el saldo, pero limitar al máximo disponible
              const faltantePorPagar = calcularFaltantePorPagar();
              const montoMaximo = Math.min(saldoDisponible, faltantePorPagar);

              montoInput.attr("max", montoMaximo.toFixed(2));
              montoInput.val(montoMaximo.toFixed(2));
              montoInput.removeClass("is-invalid");

              // Actualizar equivalente
              calcularEquivalenteUSD(pagoItem);
            } else {
              // No permitir usar saldo si es 0 o negativo
              montoInput.val("0");
              montoInput.addClass("is-invalid");
              pagoItem
                .find(".invalid-feedback")
                .text("El cliente no tiene saldo disponible");
            }
          }
        } else {
          saldoInfo.find(".saldo-disponible").text("Seleccione un cliente");
          saldoInfo.show();
          montoInput.val("0");
        }
      } else {
        // Restaurar configuración normal para otros métodos
        montoInput.removeAttr("max");
        montoInput.removeClass("is-invalid");
        pagoItem.find(".invalid-feedback").text("");
      }
    } else {
      tasaContainer.hide();
      saldoInfo.hide();
    }

    calcularEquivalenteUSD(pagoItem);
    calcularPagoConvertido.call(pagoItem);
  }

  function calcularPagoConvertido() {
    calcularTotales();
  }

  function actualizarSaldoEnPagos() {
    const clienteId = $("#cliente").val();
    if (!clienteId) return;

    const cliente = clientes.find((c) => c.id == clienteId);
    if (!cliente) return;

    // Actualizar saldo en todos los pagos existentes que usen saldo
    $(".pago-item").each(function () {
      const pagoItem = $(this);
      const metodoPago = pagoItem.find(".metodo-pago");
      const saldoInfo = pagoItem.find(".saldo-info");
      const esSaldo = metodoPago.find("option:selected").data("es-saldo");

      if (esSaldo && saldoInfo.is(":visible")) {
        const saldoDisponible = parseFloat(cliente.saldo);
        const saldoSpan = saldoInfo.find(".saldo-disponible");
        saldoSpan.text(`$${saldoDisponible.toFixed(2)}`);

        // Aplicar color según el saldo (solo positivo)
        saldoSpan.removeClass("text-success text-danger");
        if (saldoDisponible <= 0) {
          saldoSpan.addClass("text-danger");
        } else {
          saldoSpan.addClass("text-success");
        }

        const montoInput = pagoItem.find(".monto-pagado");
        if (saldoDisponible <= 0) {
          montoInput.val("0");
          montoInput.addClass("is-invalid");
          pagoItem
            .find(".invalid-feedback")
            .text("El cliente no tiene saldo disponible");
        } else {
          const faltantePorPagar = calcularFaltantePorPagar();
          const montoMaximo = Math.min(saldoDisponible, faltantePorPagar);
          montoInput.attr("max", montoMaximo.toFixed(2));
          montoInput.removeClass("is-invalid");
          pagoItem.find(".invalid-feedback").text("");

          // Actualizar valor si excede el nuevo máximo
          if (parseFloat(montoInput.val()) > montoMaximo) {
            montoInput.val(montoMaximo.toFixed(2));
          }
        }

        calcularEquivalenteUSD(pagoItem);
      }
    });

    calcularTotales();
  }

  // ========================================
  // VALIDACIÓN DE DESCUENTO
  // ========================================

  function validarDescuento() {
    const subtotal = calcularSubtotalProductos();
    const descuento = parseFloat($("#descuento").val()) || 0;
    const descuentoInput = $("#descuento");

    if (descuento > subtotal) {
      descuentoInput.addClass("is-invalid");
      descuentoInput.after(
        '<div class="invalid-feedback">El descuento no puede ser mayor al subtotal</div>'
      );
      return false;
    } else {
      descuentoInput.removeClass("is-invalid");
      descuentoInput.siblings(".invalid-feedback").remove();
      return true;
    }
  }

  function calcularSubtotalProductos() {
    let subtotal = 0;
    $(".fila-producto").each(function () {
      const precio = parseFloat($(this).find(".precio-unitario").val()) || 0;
      const cantidad = parseInt($(this).find(".cantidad").val()) || 0;
      subtotal += precio * cantidad;
    });
    return subtotal;
  }

  // ========================================
  // FUNCIONES PARA CÁLCULOS
  // ========================================

  function calcularTotales() {
    // Calcular subtotal de productos
    const subtotal = calcularSubtotalProductos();

    // Aplicar descuento con validación
    const descuento = parseFloat($("#descuento").val()) || 0;
    const total = Math.max(0, subtotal - descuento);

    // Calcular comisión
    const comisionPorcentaje =
      parseFloat($("#comision_porcentaje").val()) || 10;
    const comisionMonto = (total * comisionPorcentaje) / 100;

    // Calcular total pagado
    const totalPagado = calcularTotalPagado();

    // Determinar estado de pago y calcular exceso
    let estadoPago, estadoPagoClass;
    if (totalPagado >= total) {
      if (totalPagado > total) {
        const exceso = totalPagado - total;
        estadoPago = `EXCESO: $${exceso.toFixed(2)}`;
        estadoPagoClass = "exceso";
        // Mostrar alerta de exceso
        mostrarAdvertencia(
          `¡Atención! Hay un exceso de pago de $${exceso.toFixed(
            2
          )}. No se puede registrar la venta con exceso de pago.`
        );
      } else {
        estadoPago = "Pagado";
        estadoPagoClass = "pagado";
      }
    } else {
      estadoPago = "Pendiente";
      estadoPagoClass = "pendiente";
    }

    // Actualizar campos
    $("#subtotal").text("$" + subtotal.toFixed(2));
    $("#total").text("$" + total.toFixed(2));
    $("#total_pagado").text("$" + totalPagado.toFixed(2));
    $("#estado-pago")
      .text(estadoPago)
      .removeClass("pagado pendiente exceso")
      .addClass(estadoPagoClass);

    // Actualizar comisión en el formulario
    $("#comision").val(comisionMonto.toFixed(2));
  }

  // ========================================
  // FUNCIONES PARA LLENAR SELECTORES
  // ========================================

  function llenarSelectCliente() {
    const select = $("#cliente");
    select.empty().append('<option value="">Seleccione un cliente</option>');

    clientes.forEach(function (cliente) {
      select.append(`
                <option value="${cliente.id}">
                    ${cliente.nombre} - ${cliente.identificacion} (Saldo: $${cliente.saldo})
                </option>
            `);
    });
  }

  function llenarSelectVendedor() {
    const select = $("#vendedor");
    select.empty().append('<option value="">Seleccione un vendedor</option>');

    vendedores.forEach(function (vendedor) {
      select.append(`
                <option value="${vendedor.id}">
                    ${vendedor.nombre_completo}
                </option>
            `);
    });

    // Establecer vendedor actual por defecto
    const userId = $("#vendedor").data("user-id");
    if (userId) {
      select.val(userId);
    }
  }

  function llenarSelectFiltros() {
    // Llenar filtros de marca
    const marcas = [...new Set(productos.map((p) => p.marca).filter((m) => m))];
    const selectMarca = $("#filtroMarca");
    marcas.forEach(function (marca) {
      selectMarca.append(`<option value="${marca}">${marca}</option>`);
    });

    // Llenar filtros de tipo
    const tipos = [...new Set(productos.map((p) => p.tipo).filter((t) => t))];
    const selectTipo = $("#filtroTipo");
    tipos.forEach(function (tipo) {
      selectTipo.append(`<option value="${tipo}">${tipo}</option>`);
    });

    // Llenar filtros de talla
    const tallas = [...new Set(productos.map((p) => p.talla).filter((t) => t))];
    const selectTalla = $("#filtroTalla");
    tallas.forEach(function (talla) {
      selectTalla.append(`<option value="${talla}">${talla}</option>`);
    });
  }

  // ========================================
  // FUNCIÓN PARA ENVIAR VENTA CON VALIDACIONES
  // ========================================

  function enviarVenta(e) {
    e.preventDefault();

    // Prevenir múltiples envíos simultáneos
    if (ventaEnProceso) {
      return; // Si ya hay una venta en proceso, no hacer nada
    }

    // Deshabilitar botón inmediatamente para prevenir múltiples clics
    const submitButton = $('#venta-form button[type="submit"]');
    if (submitButton.prop('disabled')) {
      return; // Si ya está deshabilitado, no hacer nada
    }
    
    // Marcar que hay una venta en proceso
    ventaEnProceso = true;
    
    // Deshabilitar botón y mostrar loading
    submitButton.prop("disabled", true)
      .html('<i class="spinner-border spinner-border-sm me-2"></i>Procesando...');

    // Validar que haya productos
    if ($(".fila-producto").length === 0) {
      mostrarToast("Debe agregar al menos un producto", "error");
      resetearBoton();
      return;
    }

    // Validar cliente
    const clienteId = $("#cliente").val();
    if (!clienteId) {
      mostrarToast("Debe seleccionar un cliente", "error");
      resetearBoton();
      return;
    }

    // Validar vendedor
    const vendedorId = $("#vendedor").val();
    if (!vendedorId) {
      mostrarToast("Debe seleccionar un vendedor", "error");
      resetearBoton();
      return;
    }

    // Validar descuento
    if (!validarDescuento()) {
      mostrarToast("Corrija el descuento antes de continuar", "error");
      resetearBoton();
      return;
    }

    // Validar pagos
    let pagosValidos = true;
    $(".pago-item").each(function () {
      const monto = parseFloat($(this).find(".monto-pagado").val()) || 0;
      const metodo = $(this).find(".metodo-pago").val();

      if (monto <= 0 || !metodo) {
        pagosValidos = false;
        return false;
      }
    });

    if (!pagosValidos) {
      mostrarToast(
        "Todos los pagos deben tener monto y método válidos",
        "error"
      );
      resetearBoton();
      return;
    }

    // Validar que no haya exceso de pago
    const total = parseFloat($("#total").text().replace("$", "")) || 0;
    const totalPagado = calcularTotalPagado();

    if (totalPagado > total) {
      const exceso = totalPagado - total;
      mostrarToast(
        `No se puede registrar la venta con exceso de pago de $${exceso.toFixed(
          2
        )}`,
        "error"
      );
      resetearBoton();
      return;
    }

    // Recolectar datos de productos
    const productosData = [];
    $(".fila-producto").each(function () {
      const productoId = $(this).data("producto-id");
      const cantidad = parseInt($(this).find(".cantidad").val()) || 0;
      const precioUnitario =
        parseFloat($(this).find(".precio-unitario").val()) || 0;

      if (productoId && cantidad > 0 && precioUnitario > 0) {
        productosData.push({
          producto_id: productoId,
          cantidad: cantidad,
          precio_unitario: precioUnitario,
        });
      }
    });

    // Recolectar datos de pagos
    const pagosData = [];
    $(".pago-item").each(function () {
      const montoPagado = parseFloat($(this).find(".monto-pagado").val()) || 0;
      const tasa = parseFloat($(this).find(".tasa-cambio").val()) || null;
      const metodoId = $(this).find(".metodo-pago").val();

      if (montoPagado > 0 && metodoId) {
        pagosData.push({
          monto_pagado: montoPagado,
          tasa: tasa,
          metodo_id: metodoId,
        });
      }
    });

    // Preparar datos para enviar
    const ventaData = {
      cliente_id: clienteId,
      vendedor_id: $("#vendedor").val() || null,
      fecha: $("#fecha").val(),
      descuento: parseFloat($("#descuento").val()) || 0,
      comision_porcentaje: parseFloat($("#comision_porcentaje").val()) || 10,
      entrega: $("#entrega").is(":checked"),
      productos: productosData,
      pagos: pagosData,
    };

    // Verificar exceso de pago y avisar al usuario

    if (totalPagado > total) {
      const exceso = totalPagado - total;
      mostrarModalConfirmacion(
        "¡Atención!",
        `El total pagado ($${totalPagado.toFixed(
          2
        )}) excede el total de la venta ($${total.toFixed(
          2
        )}).<br><br>El exceso de $${exceso.toFixed(
          2
        )} se agregará automáticamente al saldo del cliente.<br><br>¿Desea continuar?`,
        function () {
          // Continuar con el envío de la venta
          enviarVentaConfirmada(ventaData);
        }
      );
      return; // Salir aquí, el envío se hará desde el callback del modal
    }

    // Enviar directamente si no hay exceso
    enviarVentaConfirmada(ventaData);
  }

  // ========================================
  // FUNCIONES PARA MODALES DE CONFIRMACIÓN
  // ========================================

  function mostrarModalConfirmacion(titulo, mensaje, callback) {
    // Crear modal si no existe
    if ($("#modalConfirmacion").length === 0) {
      const modalHtml = `
        <div class="modal fade" id="modalConfirmacion" tabindex="-1" aria-labelledby="modalConfirmacionLabel">
          <div class="modal-dialog modal-dialog-centered">
            <div class="modal-content">
              <div class="modal-header">
                <h5 class="modal-title" id="modalConfirmacionLabel">
                  ${titulo}
                </h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
              </div>
              <div class="modal-body">
                <p class="mb-3">${mensaje}</p>
              </div>
              <div class="modal-footer">
                <button type="button" class="btn btn-danger" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-primary" id="confirmarAccion">Aceptar</button>
              </div>
            </div>
          </div>
        </div>
      `;
      $("body").append(modalHtml);
    }

    // Actualizar contenido del modal
    $("#modalConfirmacionLabel").html(
      `<i class="fas fa-exclamation-triangle me-2"></i>${titulo}`
    );
    $("#modalConfirmacion .modal-body p").html(mensaje);

    // Limpiar eventos previos y agregar nuevo callback
    $("#confirmarAccion")
      .off("click")
      .on("click", function () {
        $("#modalConfirmacion").modal("hide");
        if (callback) callback();
      });

    // Agregar evento para cuando se cierra el modal sin confirmar
    $("#modalConfirmacion").off("hidden.bs.modal").on("hidden.bs.modal", function () {
      // Si el modal se cierra sin confirmar, reactivar el botón
      if (ventaEnProceso) {
        resetearBoton();
      }
    });

    // Mostrar modal
    $("#modalConfirmacion").modal("show");
  }

  function enviarVentaConfirmada(ventaData) {
    // El botón ya está deshabilitado desde enviarVenta, solo actualizar el texto
    $('#venta-form button[type="submit"]')
      .html('<i class="spinner-border spinner-border-sm me-2"></i>Guardando...');

    // Enviar datos
    $.ajax({
      url: "/venta/ajax/guardar-venta/",
      method: "POST",
      data: JSON.stringify(ventaData),
      contentType: "application/json",
      headers: {
        "X-CSRFToken": getCookie("csrftoken"),
      },
      success: function (response) {
        if (response.success) {
          mostrarToast("Venta registrada exitosamente", "success");
          // NO reactivar el botón aquí - la página se redirigirá
          // Redirigir después de un momento
          setTimeout(function () {
            window.location.href = "/venta/listado";
          }, 2000);
        } else {
          mostrarToast("Error al guardar la venta: " + response.error, "error");
          resetearBoton(); // Solo reactivar en caso de error
        }
      },
      error: function (xhr, status, error) {
        resetearBoton(); // Reactivar el botón en caso de error
        mostrarToast("Error de conexión al guardar la venta", "error");
        console.error("Error:", error);
      },
    });
  }

  // ========================================
  // FUNCIONES UTILITARIAS MEJORADAS
  // ========================================

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function mostrarToast(mensaje, tipo = "info") {
    // Usar el mismo estilo que los messages del sistema
    const tipoClass = {
      success: "alert-success",
      error: "alert-danger",
      warning: "alert-warning",
      info: "alert-info",
    };

    const toast = `
      <div class="mb-3 alert alert-left ${
        tipoClass[tipo]
      } alert-dismissible fade show" role="alert">
        <span>${mensaje}</span>
        <button type="button" class="btn-close btn-close-alert-${
          tipo === "error" ? "danger" : tipo
        }" data-bs-dismiss="alert" aria-label="Close"></button>
      </div>
    `;

    // Crear contenedor de toasts si no existe
    if ($("#toast-container").length === 0) {
      $("body").append(
        '<div id="toast-container" class="position-fixed top-0 end-0 p-3" style="z-index: 1100"></div>'
      );
    }

    const $toast = $(toast);
    $("#toast-container").append($toast);

    // Auto-remover después de 5 segundos
    setTimeout(function () {
      $toast.alert("close");
    }, 3000);

    // Remover del DOM después de que se oculte
    $toast.on("closed.bs.alert", function () {
      $(this).remove();
    });
  }

  // Mantener compatibilidad con funciones existentes
  function mostrarError(mensaje) {
    mostrarToast(mensaje, "error");
  }

  function mostrarExito(mensaje) {
    mostrarToast(mensaje, "success");
  }

  function mostrarAdvertencia(mensaje) {
    mostrarToast(mensaje, "warning");
  }

  function mostrarLoading() {
    $('#venta-form button[type="submit"]')
      .prop("disabled", true)
      .html(
        '<i class="spinner-border spinner-border-sm me-2"></i>Guardando...'
      );
  }

  function resetearBoton() {
    $('#venta-form button[type="submit"]')
      .prop("disabled", false)
      .html("Completar Venta");
    ventaEnProceso = false; // Resetear la variable de control
  }

  function ocultarLoading() {
    $('#venta-form button[type="submit"]')
      .prop("disabled", false)
      .html("Completar Venta");
    ventaEnProceso = false; // Resetear la variable de control
  }
});
