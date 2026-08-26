document.addEventListener('DOMContentLoaded', function () {
    const password1 = document.getElementById('id_password1') || document.getElementById('id_new_password1') || document.getElementById('id_old_password');
    const password2 = document.getElementById('id_password2') || document.getElementById('id_new_password2');
    const form = password1?.closest('form');
    // Buscar el contenedor visual del input (password-wrapper)
    const wrapper = password1?.closest('.password-wrapper');
    // Crear el div de feedback
    const feedback = document.createElement('div');
    feedback.className = 'password-feedback text-danger small mt-1';
    // Insertar el feedback DESPUÉS del wrapper
    if (wrapper && wrapper.parentNode) {
        wrapper.parentNode.insertBefore(feedback, wrapper.nextSibling);
    }

    function validatePassword(password) {
        const rules = [
            { regex: /.{16,}/, message: "Debe tener al menos 16 caracteres" },
            { regex: /[A-Z]/, message: "Debe contener al menos una mayúscula" },
            { regex: /[a-z]/, message: "Debe contener al menos una minúscula" },
            { regex: /\d/, message: "Debe contener al menos un número" },
            { regex: /[^\w\s]/, message: "Debe contener al menos un símbolo" },
        ];

        const errors = rules
            .filter(rule => !rule.regex.test(password))
            .map(rule => rule.message);

        return errors;
    }

    function mostrarErrores() {
        const value = password1.value;
        const errores = validatePassword(value);
        if (errores.length > 0) {
            feedback.innerHTML = errores.map(e => `<div>${e}</div>`).join('');
        } else {
            feedback.innerHTML = '<span class="text-success">Contraseña segura.</span>';
        }
    }

    password1?.addEventListener('input', mostrarErrores);

    form?.addEventListener('submit', function (e) {
        // Verificar primero si los campos obligatorios están completos
        // Para el formulario de usuarios, los campos obligatorios son: username, password1, password2, group
        const username = form.querySelector('#id_username');
        const group = form.querySelector('#id_group');
        
        let hasEmptyRequired = false;
        
        // Verificar username (si existe)
        if (username && !username.value.trim()) {
            hasEmptyRequired = true;
            username.classList.add('is-invalid');
        } else if (username) {
            username.classList.remove('is-invalid');
        }
        
        // Verificar group (si existe)
        if (group && !group.value) {
            hasEmptyRequired = true;
            group.classList.add('is-invalid');
        } else if (group) {
            group.classList.remove('is-invalid');
        }
        
        // Verificar password1 (si existe y es obligatorio)
        if (password1 && !password1.value.trim()) {
            hasEmptyRequired = true;
            password1.classList.add('is-invalid');
        } else if (password1) {
            password1.classList.remove('is-invalid');
        }
        
        // Si hay campos obligatorios vacíos, no validar contraseña
        if (hasEmptyRequired) {
            return; // Permitir que Django maneje los errores de campos obligatorios
        }
        
        // Solo validar contraseña si los campos obligatorios están completos
        const errores = validatePassword(password1.value);
        if (errores.length > 0) {
            e.preventDefault();
            mostrarErrores();
        }
    });

    // Validación de confirmación de contraseña
    if (password2) {
        // Crear el div de feedback para password2
        const wrapper2 = password2.closest('.password-wrapper');
        const feedback2 = document.createElement('div');
        feedback2.className = 'password-feedback text-danger small mt-1';
        if (wrapper2 && wrapper2.parentNode) {
            wrapper2.parentNode.insertBefore(feedback2, wrapper2.nextSibling);
        }

        function validarCoincidencia() {
            if (password2.value && password1.value !== password2.value) {
                feedback2.innerHTML = 'Las contraseñas no coinciden';
            } else if (password2.value) {
                feedback2.innerHTML = '<span class="text-success">Las contraseñas coinciden.</span>';
            } else {
                feedback2.innerHTML = '';
            }
        }

        password1.addEventListener('input', validarCoincidencia);
        password2.addEventListener('input', validarCoincidencia);

        form?.addEventListener('submit', function (e) {
            // Verificar primero si los campos obligatorios están completos
            // Para el formulario de usuarios, los campos obligatorios son: username, password1, password2, group
            const username = form.querySelector('#id_username');
            const group = form.querySelector('#id_group');
            
            let hasEmptyRequired = false;
            
            // Verificar username (si existe)
            if (username && !username.value.trim()) {
                hasEmptyRequired = true;
                username.classList.add('is-invalid');
            } else if (username) {
                username.classList.remove('is-invalid');
            }
            
            // Verificar group (si existe)
            if (group && !group.value) {
                hasEmptyRequired = true;
                group.classList.add('is-invalid');
            } else if (group) {
                group.classList.remove('is-invalid');
            }
            
            // Verificar password1 (si existe y es obligatorio)
            if (password1 && !password1.value.trim()) {
                hasEmptyRequired = true;
                password1.classList.add('is-invalid');
            } else if (password1) {
                password1.classList.remove('is-invalid');
            }
            
            // Verificar password2 (si existe y es obligatorio)
            if (password2 && !password2.value.trim()) {
                hasEmptyRequired = true;
                password2.classList.add('is-invalid');
            } else if (password2) {
                password2.classList.remove('is-invalid');
            }
            
            // Si hay campos obligatorios vacíos, no validar contraseña
            if (hasEmptyRequired) {
                return; // Permitir que Django maneje los errores de campos obligatorios
            }
            
            // Solo validar confirmación de contraseña si los campos obligatorios están completos
            if (password2.value !== password1.value) {
                e.preventDefault();
                feedback2.innerHTML = 'Las contraseñas no coinciden';
            }
        });
    }
});
