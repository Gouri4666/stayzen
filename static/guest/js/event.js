document.addEventListener("DOMContentLoaded", () => {

    /* ==========================
       CARD SCROLL ANIMATION
    ========================== */

    const cards = document.querySelectorAll(".hall-card");

    const observer = new IntersectionObserver((entries) => {

        entries.forEach(entry => {

            if(entry.isIntersecting){

                entry.target.classList.add("show-card");

            }

        });

    },{
        threshold:0.15
    });

    cards.forEach(card => {

        card.classList.add("hidden-card");
        observer.observe(card);

    });


    /* ==========================
       BOOKING SIDEBAR
    ========================== */

    const sidebar = document.getElementById("bookingSidebar");

    const overlay = document.createElement("div");
    overlay.classList.add("page-overlay");
    document.body.appendChild(overlay);

    document.querySelectorAll(".openBooking").forEach(button => {

        button.addEventListener("click",(e)=>{

            e.preventDefault();

            const hallId = button.getAttribute("data-hall-id");
            const hallSelect = sidebar.querySelector("select[name='hall_id']");
            if (hallSelect && hallId) {
                hallSelect.value = hallId;
                hallSelect.dispatchEvent(new Event('change'));
            }

            sidebar.classList.add("active");
            overlay.classList.add("active");

            document.body.style.overflow="hidden";

        });

    });

    document.getElementById("closeBooking").addEventListener("click", closeSidebar);

    overlay.addEventListener("click", closeSidebar);

    function closeSidebar(){

        sidebar.classList.remove("active");
        overlay.classList.remove("active");

        document.body.style.overflow="auto";

    }


    /* ==========================
       BUTTON RIPPLE EFFECT
    ========================== */

    document.querySelectorAll(".btn").forEach(button => {

        button.addEventListener("click", function(e){

            const circle = document.createElement("span");

            const diameter = Math.max(
                this.clientWidth,
                this.clientHeight
            );

            circle.style.width = circle.style.height = `${diameter}px`;

            circle.style.left =
                `${e.clientX - this.offsetLeft - diameter / 2}px`;

            circle.style.top =
                `${e.clientY - this.offsetTop - diameter / 2}px`;

            circle.classList.add("ripple");

            const ripple = this.querySelector(".ripple");

            if(ripple){
                ripple.remove();
            }

            this.appendChild(circle);

        });

    });

});