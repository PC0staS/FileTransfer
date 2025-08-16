// Funcionalidad para mostrar/ocultar contraseña
document.addEventListener('DOMContentLoaded', function() {
    const passwordInput = document.getElementById('password');
    const toggleBtn = document.getElementById('togglePassword');
    
    if (passwordInput && toggleBtn) {
        toggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            const currentType = passwordInput.type;
            const newType = currentType === 'password' ? 'text' : 'password';
            passwordInput.type = newType;
            
            // Actualizar el icono y texto del botón
            if (newType === 'text') {
                this.innerHTML = '<span class="bi bi-eye-slash"></span> Ocultar';
            } else {
                this.innerHTML = '<span class="bi bi-eye"></span> Mostrar';
            }
        });
    }

    // Validación en cliente: mínimo 8, al menos 1 mayúscula y 1 número
    const pwInline = document.getElementById('pwInline');
    const pwLen = document.getElementById('pwLen');
    const pwUpper = document.getElementById('pwUpper');
    const pwNum = document.getElementById('pwNum');

    function evaluatePassword(pw) {
        const hasLen = pw.length >= 8;
        const hasUpper = /[A-Z]/.test(pw);
        const hasNum = /\d/.test(pw);

        // show inline block when user is typing, hide when empty
        if (pwInline) {
            if (pw) pwInline.classList.add('visible');
            else pwInline.classList.remove('visible');
        }

        if (pwLen) pwLen.classList.toggle('text-success', hasLen);
        if (pwLen) pwLen.classList.toggle('text-danger', !hasLen);
        if (pwUpper) pwUpper.classList.toggle('text-success', hasUpper);
        if (pwUpper) pwUpper.classList.toggle('text-danger', !hasUpper);
        if (pwNum) pwNum.classList.toggle('text-success', hasNum);
        if (pwNum) pwNum.classList.toggle('text-danger', !hasNum);

        return hasLen && hasUpper && hasNum;
    }

    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            evaluatePassword(this.value);
        });
        // hide inline feedback when input loses focus and password empty
        passwordInput.addEventListener('blur', function() {
            if (!this.value && pwInline) pwInline.classList.remove('visible');
        });
    }

    // Prevent submit if password is weak
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const pw = form.querySelector('#password');
            if (pw) {
                const ok = evaluatePassword(pw.value);
                if (!ok) {
                    e.preventDefault();
                    // ensure inline rules are visible
                    if (pwInline) pwInline.classList.add('visible');
                    // also show an inline alert for clarity
                    const alertDiv = document.createElement('div');
                    alertDiv.className = 'alert alert-danger alert-dismissible fade show';
                    alertDiv.role = 'alert';
                    alertDiv.innerHTML = '<strong>Error:</strong> La contraseña no cumple los requisitos.' +
                        '<button type="button" class="btn-close" data-bs-dismiss="alert"></button>';
                    form.prepend(alertDiv);
                    setTimeout(() => {
                        const bsAlert = new bootstrap.Alert(alertDiv);
                        bsAlert.close();
                    }, 5000);
                }
            }
        }, { passive: false });
    });
    
    // Mejorar la experiencia de usuario con animaciones suaves
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Enviando...';
                submitBtn.disabled = true;
            }
        });
    });
    
    // Animación para los botones al hacer hover
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-2px)';
        });
        
        btn.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });
    
    // Auto-dismiss para alertas después de 5 segundos
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (alert.classList.contains('alert-success')) {
            setTimeout(() => {
                const bsAlert = new bootstrap.Alert(alert);
                bsAlert.close();
            }, 5000);
        }
    });
});