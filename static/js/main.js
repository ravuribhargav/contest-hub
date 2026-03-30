
document.addEventListener('DOMContentLoaded', function () {

  // COUNTDOWN
  document.querySelectorAll('.js-countdown[data-countdown-target]').forEach(function(cdEl) {
    var target = parseInt(cdEl.dataset.countdownTarget, 10) * 1000;
    if (isNaN(target)) return;

    function pad(n) { return String(n).padStart(2, '0'); }

    function tick() {
      var diff = target - Date.now();
      if (diff < 0) diff = 0;
      var d = Math.floor(diff / 86400000);
      var h = Math.floor((diff % 86400000) / 3600000);
      var m = Math.floor((diff % 3600000) / 60000);
      var s = Math.floor((diff % 60000) / 1000);

      var dEl = cdEl.querySelector('[data-part="days"]');
      var hEl = cdEl.querySelector('[data-part="hours"]');
      var mEl = cdEl.querySelector('[data-part="minutes"]');
      var sEl = cdEl.querySelector('[data-part="seconds"]');

      if (dEl) dEl.textContent = pad(d);
      if (hEl) hEl.textContent = pad(h);
      if (mEl) mEl.textContent = pad(m);
      if (sEl) sEl.textContent = pad(s);
    }

    tick();
    setInterval(tick, 1000);
  });

  // COPY CODE
  document.querySelectorAll('[data-copy]').forEach(function(btn) {
    btn.addEventListener('click', function() {
      var text = this.dataset.copy;
      navigator.clipboard.writeText(text).then(function() {
        var orig = btn.innerHTML;
        btn.innerHTML = '&#10003; Copied!';
        btn.classList.add('copy-feedback');
        setTimeout(function() {
          btn.innerHTML = orig;
          btn.classList.remove('copy-feedback');
        }, 1600);
      });
    });
  });

  // AUTO DISMISS ALERTS
  document.querySelectorAll('.alert-b').forEach(function(el) {
    setTimeout(function() { el.style.transition = 'opacity 0.4s'; el.style.opacity = '0'; setTimeout(function(){ el.remove(); }, 400); }, 5000);
  });

  // HOME SEARCH
  var sf = document.getElementById('home-search');
  if (sf) {
    sf.addEventListener('submit', function(e) {
      e.preventDefault();
      var q = sf.querySelector('input').value.trim();
      if (q) window.location.href = '/contests/?q=' + encodeURIComponent(q);
    });
  }

  // STAT NUMBER ANIMATION
  var ios = new IntersectionObserver(function(entries) {
    entries.forEach(function(entry) {
      if (entry.isIntersecting) {
        var el = entry.target;
        var t = parseInt(el.dataset.target, 10);
        if (!isNaN(t) && t > 0) {
          var cur = 0;
          var step = Math.max(1, Math.ceil(t / 50));
          var timer = setInterval(function() {
            cur = Math.min(cur + step, t);
            el.textContent = cur.toLocaleString();
            if (cur >= t) clearInterval(timer);
          }, 25);
        }
        ios.unobserve(el);
      }
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('.stat-num[data-target]').forEach(function(el) { ios.observe(el); });

  // CONFIRM
  document.querySelectorAll('[data-confirm]').forEach(function(el) {
    el.addEventListener('click', function(e) {
      if (!confirm(this.dataset.confirm)) e.preventDefault();
    });
  });
});
