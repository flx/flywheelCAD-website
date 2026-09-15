// flywheelcad.com — small progressive enhancements. Every page works without it.
(() => {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Videos marked data-autoplay play while at least half visible and pause
  // off-screen. Under reduced motion they never start; the poster and the
  // native controls stay.
  const videos = Array.from(document.querySelectorAll("video[data-autoplay]"));
  if (videos.length) {
    if (reduceMotion) {
      videos.forEach((v) => { v.controls = true; });
    } else if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => {
          const v = e.target;
          if (e.isIntersecting) {
            const p = v.play();
            if (p && p.catch) p.catch(() => { v.controls = true; });
          } else {
            v.pause();
          }
        });
      }, { threshold: 0.5 });
      videos.forEach((v) => io.observe(v));
    } else {
      videos.forEach((v) => { v.controls = true; });
    }
  }

  // Lightbox for manual screenshots (links with class lightbox-trigger).
  const triggers = Array.from(document.querySelectorAll(".lightbox-trigger"));
  if (!triggers.length) return;

  const overlay = document.createElement("div");
  overlay.className = "lightbox-overlay";
  overlay.hidden = true;
  overlay.innerHTML =
    '<div class="lightbox-shell" role="dialog" aria-modal="true" aria-label="Image preview">' +
    '<button class="lightbox-close" type="button" aria-label="Close image preview">&times;</button>' +
    '<div class="lightbox-stage"><img class="lightbox-image" alt=""></div>' +
    '<p class="lightbox-caption"></p></div>';
  document.body.appendChild(overlay);

  const dialog = overlay.querySelector(".lightbox-shell");
  const closeButton = overlay.querySelector(".lightbox-close");
  const image = overlay.querySelector(".lightbox-image");
  const caption = overlay.querySelector(".lightbox-caption");
  let lastTrigger = null;

  function open(trigger) {
    const thumb = trigger.querySelector("img");
    image.src = trigger.href;
    image.alt = thumb ? thumb.alt : "";
    caption.textContent = trigger.dataset.lightboxCaption || (thumb ? thumb.alt : "");
    overlay.hidden = false;
    document.body.classList.add("lightbox-open");
    closeButton.focus();
    lastTrigger = trigger;
  }

  function close() {
    if (overlay.hidden) return;
    overlay.hidden = true;
    image.removeAttribute("src");
    caption.textContent = "";
    document.body.classList.remove("lightbox-open");
    if (lastTrigger) lastTrigger.focus();
  }

  triggers.forEach((t) => t.addEventListener("click", (e) => { e.preventDefault(); open(t); }));
  overlay.addEventListener("click", (e) => {
    if (!dialog.contains(e.target) || e.target.classList.contains("lightbox-stage")) close();
  });
  closeButton.addEventListener("click", close);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });
})();
