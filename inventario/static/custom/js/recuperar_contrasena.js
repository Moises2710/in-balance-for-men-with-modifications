document.addEventListener('DOMContentLoaded', function () {
    console.log('Script de recuperación de contraseña cargado');

    const form = document.querySelector('.login-form');
    if (!form) {
        console.error('No se encontró el formulario');
        return;
    }

    let errorContainer = form.querySelector('.error-messages');
    if (!errorContainer) {
        errorContainer = document.createElement('div');
        errorContainer.className = 'error-messages';
        form.insertBefore(errorContainer, form.firstChild);
    }

    form.addEventListener('submit', function (event) {
        event.preventDefault(); // Evitar el envío del formulario
        console.log('Formulario enviado');

        // Limpiar mensajes de error previos
        errorContainer.innerHTML = '';

        // Obtener el correo ingresado
        const email = document.getElementById('email').value.trim();
        console.log('Correo ingresado:', email);

        // Validar que el campo no esté vacío y tenga un formato correcto
        let errores = [];
        if (!email) {
            errores.push('El campo de correo electrónico es obligatorio.');
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
            errores.push('Por favor, introduce un correo electrónico válido.');
        }

        // Si hay errores, mostrarlos y detener la ejecución
        if (errores.length > 0) {
            errores.forEach(mensaje => mostrarError(mensaje));
            return;
        }

        // Mostrar indicador de carga
        const submitButton = form.querySelector('button[type="submit"]');
        const originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = 'Enviando...';
        
        // Enviar la solicitud AJAX
        enviarFormulario(email).finally(() => {
            // Restaurar botón
            submitButton.disabled = false;
            submitButton.textContent = originalText;
        });
    });

    function mostrarError(mensaje) {
        const errorElement = document.createElement('p');
        errorElement.className = 'alert alert-danger';
        errorElement.textContent = mensaje;
        errorContainer.appendChild(errorElement);
    }

    function mostrarExito(mensaje) {
        const successElement = document.createElement('p');
        successElement.className = 'alert alert-success';
        successElement.textContent = mensaje;
        errorContainer.appendChild(successElement);
    }

    function enviarFormulario(email) {
        const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;

        // Crear un timeout para evitar esperas infinitas
        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            console.log('Timeout activado - cancelando solicitud');
            controller.abort();
        }, 20000); // 20 segundos timeout (reducido para evitar 502)

        return fetch(window.location.href, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken,
                'X-Requested-With': 'XMLHttpRequest'  // Indica que es una petición AJAX
            },
            body: new URLSearchParams({ 'email': email }),
            signal: controller.signal
        })
        .then(response => {
            console.log('Respuesta del servidor:', {
                status: response.status,
                statusText: response.statusText,
                contentType: response.headers.get('content-type'),
                ok: response.ok
            });
            
            // Verificar primero si la respuesta es OK
            if (!response.ok) {
                // Intentar parsear como JSON para obtener el error específico
                return response.json().then(data => {
                    throw new Error(data.error || 'Error en el servidor');
                }).catch(() => {
                    // Si no es JSON válido, usar el texto de respuesta
                    return response.text().then(text => {
                        console.error('Respuesta de error no-JSON:', text);
                        throw new Error(`Error del servidor: ${response.status} ${response.statusText}`);
                    });
                });
            }
            
            // Respuesta exitosa - verificar que sea JSON válido
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return response.json();
            } else {
                // Si no fue JSON válido, probablemente es HTML - tratar como éxito con redirect
                console.warn('Respuesta exitosa pero no es JSON:', contentType);
                return {
                    success: true,
                    message: 'Se han enviado instrucciones a tu correo electrónico.',
                    redirect_url: '/login/'
                };
            }
        })
        .then(data => {
            clearTimeout(timeoutId); // Limpiar el timeout
            console.log('Respuesta recibida:', data);

            // Limpiar mensajes previos
            errorContainer.innerHTML = '';

            if (data.success) {
                mostrarExito(data.message || 'Se han enviado instrucciones a tu correo electrónico.');

                // Redirigir después de 3 segundos si hay un redirect_url
                if (data.redirect_url) {
                    setTimeout(() => {
                        window.location.href = data.redirect_url;
                    }, 3000);
                }
            } else {
                mostrarError(data.error || 'Ocurrió un error. Inténtalo de nuevo.');
            }
        })
                .catch(error => {
                    console.error('Error en la solicitud:', error);
                    clearTimeout(timeoutId); // Limpiar el timeout

                    if (error.name === 'AbortError') {
                        mostrarError('La solicitud tardó demasiado tiempo. Por favor, verifica tu conexión e intenta de nuevo.');
                    } else if (error.message.includes('502')) {
                        mostrarError('El servidor está temporalmente sobrecargado. Por favor, espera unos momentos e intenta de nuevo.');
                    } else {
                        mostrarError(error.message || 'Hubo un problema con la solicitud. Inténtalo de nuevo.');
                    }
                });
    }
});