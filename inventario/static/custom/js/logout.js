console.log("Probando logout.js");
document.addEventListener('DOMContentLoaded', function() {
    const logoutLink = document.getElementById('logout-link');
    const logoutForm = document.getElementById('logout-form');
    const confirmModal = document.getElementById('confirmLogoutModal');
    const confirmBtn = document.getElementById('confirmLogoutBtn');

    if (logoutLink && logoutForm && confirmModal && confirmBtn) {
        // Usar Bootstrap Modal
        const bsModal = new bootstrap.Modal(confirmModal);

        logoutLink.addEventListener('click', function(e) {
            e.preventDefault();
            bsModal.show();
        });

        confirmBtn.addEventListener('click', function() {
            bsModal.hide();
            logoutForm.submit();
        });
    }
});