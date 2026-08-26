document.addEventListener('DOMContentLoaded', function () {
    const loginForm = document.getElementById('login-form');
    const captchaContainer = document.querySelector('.form-group:has(label[for*="captcha"]) > div');
    const errorContainer = document.querySelector('.error-messages');
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');
    const captchaInput = document.getElementById('id_captcha_1');
    const recaptchaTokenInput = document.querySelector('input[name="recaptcha_token"]');

    if (!loginForm || !errorContainer || !usernameInput || !passwordInput) return;

    function clearGeneralError() {
        errorContainer.innerHTML = '';
    }

    usernameInput.addEventListener('focus', clearGeneralError);
    passwordInput.addEventListener('focus', clearGeneralError);
    usernameInput.addEventListener('input', clearGeneralError);
    passwordInput.addEventListener('input', clearGeneralError);
    
    // Agregar listeners para captcha si existe
    if (captchaInput) {
        captchaInput.addEventListener('focus', clearGeneralError);
        captchaInput.addEventListener('input', clearGeneralError);
    }

    // Función para ejecutar reCAPTCHA v3
    function executeRecaptcha() {
        return new Promise((resolve, reject) => {
           
            
            // Timeout de 10 segundos
            const timeout = setTimeout(() => {
                
                reject('Timeout ejecutando reCAPTCHA v3');
            }, 10000);
            
            if (typeof grecaptcha === 'undefined') {
                
                clearTimeout(timeout);
                reject('reCAPTCHA no está disponible');
                return;
            }
            
            const siteKey = window.RECAPTCHA_V3_SITE_KEY;
            if (!siteKey) {
                
                clearTimeout(timeout);
                reject('reCAPTCHA v3 Site Key no está configurada');
                return;
            }
            
            try {
                // Verificar si grecaptcha.enterprise.execute existe (reCAPTCHA v3 Enterprise)
                if (typeof grecaptcha.enterprise !== 'undefined' && typeof grecaptcha.enterprise.execute === 'function') {
                    grecaptcha.enterprise.execute(siteKey, {action: 'login'})
                        .then(function(token) {
                            clearTimeout(timeout);
                            resolve(token);
                        })
                        .catch(function(error) {
                            clearTimeout(timeout);
                            reject(error);
                        });
                }
                // Fallback a la API estándar de reCAPTCHA v3
                else if (typeof grecaptcha.execute === 'function') {
                    
                    grecaptcha.execute(siteKey, {action: 'login'})
                        .then(function(token) {
                            clearTimeout(timeout);
                            
                            resolve(token);
                        })
                        .catch(function(error) {
                            clearTimeout(timeout);
                            
                            reject(error);
                        });
                }
                else {
                    
                    clearTimeout(timeout);
                    reject('Ninguna API de reCAPTCHA v3 disponible');
                    return;
                }
            } catch (error) {
                clearTimeout(timeout);
                console.error('Error ejecutando reCAPTCHA:', error);
                reject('Error ejecutando reCAPTCHA: ' + error.message);
            }
        });
    }

    loginForm.addEventListener('submit', function (event) {
        event.preventDefault();

        ['username', 'password'].forEach(id => {
            const input = document.getElementById(id);
            if (input) {
                input.classList.remove('is-invalid');
                let nextSibling = input.nextElementSibling;
                while (nextSibling && nextSibling.classList.contains('invalid-feedback')) {
                    nextSibling.remove();
                    nextSibling = nextSibling.nextElementSibling;
                }
            }
        });
        
        // Limpiar errores de captcha si existe
        const captchaInputElement = document.getElementById('id_captcha_1');
        if (captchaInputElement) {
            captchaInputElement.classList.remove('is-invalid');
            let nextSibling = captchaInputElement.nextElementSibling;
            while (nextSibling && nextSibling.classList.contains('invalid-feedback')) {
                nextSibling.remove();
                nextSibling = captchaInputElement.nextElementSibling;
            }
        }

        const username = document.getElementById('username')?.value.trim();
        const password = document.getElementById('password')?.value.trim();
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        const captchaChallenge = document.querySelector('[name="captcha_0"]')?.value;
        const captchaResponse = document.getElementById('id_captcha_1')?.value.trim();

        if (!csrfToken) {
            mostrarErrores(['Error: Token CSRF no encontrado.']);
            return;
        }

        // Intentar obtener token de reCAPTCHA v3
        executeRecaptcha()
            .then(function(recaptchaToken) {
                
                // Si reCAPTCHA v3 funciona, usar ese token
                if (recaptchaTokenInput) {
                    recaptchaTokenInput.value = recaptchaToken;
                }
                submitForm(username, password, csrfToken, captchaChallenge, captchaResponse, recaptchaToken);
            })
            .catch(function(error) {
                
                // Si reCAPTCHA v3 falla, usar captcha tradicional
                submitForm(username, password, csrfToken, captchaChallenge, captchaResponse, null);
            });
    });

    function submitForm(username, password, csrfToken, captchaChallenge, captchaResponse, recaptchaToken) {
        const formData = new URLSearchParams({
            username: username,
            password: password,
            csrfmiddlewaretoken: csrfToken,
            captcha_0: captchaChallenge,
            captcha_1: captchaResponse
        });

        // Agregar token de reCAPTCHA v3 si está disponible
        if (recaptchaToken) {
            formData.append('recaptcha_token', recaptchaToken);
        }

        
        
        fetch(loginForm.action, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken
            },
            body: formData,
        })
        .then(response => {
            
            return response.json().then(data => ({ status: response.status, data }));
        })
        .then(({ status, data }) => {
            
            if (status === 200 && data.success) {
                window.location.href = data.redirect_url;
            } else {
                mostrarErrores(data.errors);
                // Actualizar captcha si es necesario
                if (data.update_captcha) {
                    fetch(window.location.pathname)
                        .then(response => response.text())
                        .then(html => {
                            const parser = new DOMParser();
                            const doc = parser.parseFromString(html, 'text/html');
                            const newCaptchaContainer = doc.querySelector('.form-group:has(label[for*="captcha"]) > div');
                            const currentCaptchaContainer = document.querySelector('.form-group:has(label[for*="captcha"]) > div');
                            
                            if (newCaptchaContainer && currentCaptchaContainer) {
                                currentCaptchaContainer.innerHTML = newCaptchaContainer.innerHTML;
                            } else if (newCaptchaContainer) {
                                // Si no existe el contenedor actual, agregarlo
                                const formGroup = document.querySelector('.form-group:has(label[for*="captcha"])');
                                if (formGroup) {
                                    formGroup.innerHTML = newCaptchaContainer.parentElement.innerHTML;
                                }
                            }
                        });
                }
            }
        })
        .catch((error) => {
            console.error('Error en la petición:', error);
            mostrarErrores(['Error de conexión con el servidor.']);
        });
    }

    function mostrarErrores(errores) {
        // Limpiar mensajes de error individuales del captcha
        const captchaInputElement = document.getElementById("id_captcha_1");
        if (captchaInputElement) {
            captchaInputElement.classList.remove('is-invalid');
            let nextSibling = captchaInputElement.nextElementSibling;
            while (nextSibling && nextSibling.classList.contains('invalid-feedback')) {
                nextSibling.remove();
                nextSibling = captchaInputElement.nextElementSibling;
            }
        }
    
        // Limpiar el contenedor de errores generales
        const errorContainer = document.querySelector('.error-messages');
        if (errorContainer) {
            errorContainer.innerHTML = '';
        }
    
        for (const campo in errores) {
            const mensaje = errores[campo];
    
            if (campo === '__all__') {
                // Mostrar error general de usuario o contraseña incorrectos
                if (errorContainer) {
                    errorContainer.innerHTML = `
                        <div class="alert alert-danger alert-dismissible fade show" role="alert">
                            ${mensaje}
                            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                        </div>
                    `;
                }
            } else if (campo === "captcha") {
                // Mostrar error de captcha debajo del campo
                if (captchaInputElement) {
                    captchaInputElement.classList.add('is-invalid');
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'invalid-feedback';
                    errorDiv.textContent = mensaje;
                    captchaInputElement.parentNode.insertBefore(errorDiv, captchaInputElement.nextSibling);
                }
            }
        }
    }
});