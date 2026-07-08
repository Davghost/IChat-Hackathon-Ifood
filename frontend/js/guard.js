document.addEventListener("DOMContentLoaded", () => {

    if (!Auth.isLoggedIn()) {

        window.location.href = "login.html"

    }

})