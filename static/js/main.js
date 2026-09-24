// main.js — students will add JavaScript here as features are built

(function () {
    var openBtn = document.getElementById("see-how-it-works");
    var overlay = document.getElementById("how-it-works-modal");
    var closeBtn = document.getElementById("how-it-works-close");
    var iframe = document.getElementById("how-it-works-video");

    if (!openBtn || !overlay || !closeBtn || !iframe) {
        return;
    }

    var videoSrc = iframe.getAttribute("data-src") || "";

    function openModal() {
        iframe.src = videoSrc;
        overlay.hidden = false;
        overlay.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        closeBtn.focus();
    }

    function closeModal() {
        overlay.hidden = true;
        overlay.setAttribute("aria-hidden", "true");
        // Clear src so YouTube stops audio/video in the background
        iframe.src = "";
        document.body.style.overflow = "";
        openBtn.focus();
    }

    openBtn.addEventListener("click", openModal);
    closeBtn.addEventListener("click", closeModal);

    overlay.addEventListener("click", function (event) {
        if (event.target === overlay) {
            closeModal();
        }
    });

    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && !overlay.hidden) {
            closeModal();
        }
    });
})();
