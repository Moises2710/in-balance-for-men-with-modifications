/**
 * Validaciones dinámicas para cambio de contraseña (sin indicadores visuales)
 */
$(document).ready(function() {
    // Lista de contraseñas comunes
    const commonPasswords = [
        'password', '123456', '123456789', 'qwerty', 'abc123', 'password123',
        'admin', 'letmein', 'welcome', 'monkey', 'dragon', 'master', 'hello',
        'freedom', 'whatever', 'qazwsx', 'trustno1', 'jordan', 'harley',
        'ranger', 'iwantu', 'jennifer', 'hunter', 'buster', 'soccer',
        'baseball', 'tiger', 'charlie', 'andrew', 'michelle', 'love',
        'sunshine', 'jessica', 'asshole', '696969', 'amanda', 'access',
        'yankees', '987654321', 'dallas', 'austin', 'thunder', 'taylor',
        'matrix', 'mobilemail', 'mom', 'monitor', 'monitoring', 'montana',
        'moon', 'moscow', 'mother', 'movie', 'mozilla', 'music', 'mustang',
        'password', 'pa$$w0rd', 'p@ssw0rd', 'p@$$w0rd', 'pass123', 'pass1234',
        '12345678', 'qwerty123', 'admin123', 'letmein123', 'welcome123'
    ];
    
    /**
     * Valida una contraseña según los requisitos establecidos
     * @param {string} password - La contraseña a validar
     * @returns {object} - Objeto con el estado de cada validación
     */
    function validatePassword(password) {
        const validations = {
            length: password.length >= 8,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            number: /\d/.test(password),
            special: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(password),
            common: !commonPasswords.includes(password.toLowerCase())
        };
        
        return validations;
    }
    
    /**
     * Valida que las contraseñas coincidan
     * @param {string} password - Primera contraseña
     * @param {string} confirmation - Segunda contraseña
     * @returns {boolean} - True si coinciden
     */
    function validatePasswordConfirmation(password, confirmation) {
        return password === confirmation && password.length > 0;
    }
    
    /**
     * Habilita o deshabilita el botón de envío según las validaciones
     */
    function updateSubmitButton() {
        const newPassword = $('#id_new_password1').val();
        const confirmPassword = $('#id_new_password2').val();
        const oldPassword = $('#id_old_password').val();
        
        const passwordValidations = validatePassword(newPassword);
        const passwordValid = Object.values(passwordValidations).every(v => v);
        const confirmationValid = validatePasswordConfirmation(newPassword, confirmPassword);
        const oldPasswordFilled = oldPassword.length > 0;
        
        const submitBtn = $('#submit-btn');
        submitBtn.prop('disabled', !(passwordValid && confirmationValid && oldPasswordFilled));
        
        // Cambiar el estilo del botón
        if (submitBtn.prop('disabled')) {
            submitBtn.removeClass('btn-success').addClass('btn-primary');
        } else {
            submitBtn.removeClass('btn-primary').addClass('btn-success');
        }
    }
    
    /**
     * Maneja el toggle de visibilidad de contraseña
     */
    function setupPasswordToggles() {
        $('.password-toggle').on('click', function() {
            const targetId = $(this).data('target');
            const input = $('#' + targetId);
            const icon = $(this);
            
            if (input.attr('type') === 'password') {
                input.attr('type', 'text');
                icon.attr('src', '/static/assets/images/svg/eye-slash.svg');
                icon.attr('alt', 'Ocultar contraseña');
            } else {
                input.attr('type', 'password');
                icon.attr('src', '/static/assets/images/svg/eye.svg');
                icon.attr('alt', 'Mostrar contraseña');
            }
        });
    }
    
    /**
     * Configura los event listeners para las validaciones
     */
    function setupEventListeners() {
        // Validación de nueva contraseña
        $('#id_new_password1').on('input', function() {
            updateSubmitButton();
        });
        
        // Validación de confirmación de contraseña
        $('#id_new_password2').on('input', function() {
            updateSubmitButton();
        });
        
        // Validación de contraseña actual
        $('#id_old_password').on('input', function() {
            updateSubmitButton();
        });
        
        // Prevenir envío si el formulario no es válido
        $('#password-change-form').on('submit', function(e) {
            const newPassword = $('#id_new_password1').val();
            const confirmPassword = $('#id_new_password2').val();
            const oldPassword = $('#id_old_password').val();
            
            const passwordValidations = validatePassword(newPassword);
            const passwordValid = Object.values(passwordValidations).every(v => v);
            const confirmationValid = validatePasswordConfirmation(newPassword, confirmPassword);
            const oldPasswordFilled = oldPassword.length > 0;
            
            if (!(passwordValid && confirmationValid && oldPasswordFilled)) {
                e.preventDefault();
                alert('Por favor, completa todos los campos correctamente antes de enviar el formulario.');
                return false;
            }
            
            // Permitir que el formulario se envíe para que Django valide la contraseña actual
            return true;
        });
    }
    
    /**
     * Inicializa todas las funcionalidades
     */
    function init() {
        setupPasswordToggles();
        setupEventListeners();
        updateSubmitButton();
    }
    
    // Inicializar cuando el DOM esté listo
    init();
}); 