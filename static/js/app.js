/* Petites interactions communes à toutes les pages (aucune dépendance). */
(function () {
  "use strict";

  /* --- Menu latéral sur mobile -------------------------------------------- */
  var bouton = document.querySelector(".menu-toggle");
  var menu = document.querySelector(".sidebar");

  function basculerMenu(ouvrir) {
    if (!menu || !bouton) return;
    menu.classList.toggle("open", ouvrir);
    document.body.classList.toggle("menu-ouvert", ouvrir);
    bouton.setAttribute("aria-expanded", String(ouvrir));
    bouton.setAttribute("aria-label", ouvrir ? "Fermer le menu" : "Ouvrir le menu");
    if (ouvrir) {
      var premierLien = menu.querySelector(".side-nav a");
      if (premierLien) premierLien.focus({ preventScroll: true });
    }
  }

  if (bouton && menu) {
    bouton.addEventListener("click", function () {
      basculerMenu(!menu.classList.contains("open"));
    });
    document.querySelectorAll("[data-fermer-menu]").forEach(function (el) {
      el.addEventListener("click", function () { basculerMenu(false); });
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menu.classList.contains("open")) {
        basculerMenu(false);
        bouton.focus();
      }
    });
    // Glisser vers la gauche pour fermer le menu (Android / iOS)
    var debutX = null;
    menu.addEventListener("touchstart", function (e) { debutX = e.touches[0].clientX; }, { passive: true });
    menu.addEventListener("touchend", function (e) {
      if (debutX !== null && debutX - e.changedTouches[0].clientX > 60) basculerMenu(false);
      debutX = null;
    }, { passive: true });
    window.matchMedia("(min-width: 821px)").addEventListener("change", function (m) {
      if (m.matches) basculerMenu(false);
    });
  }

  /* --- Tableaux lisibles sur téléphone ------------------------------------
     Chaque cellule reçoit le titre de sa colonne (data-label) : en dessous de
     560 px, le CSS affiche alors chaque ligne comme une carte. */
  document.querySelectorAll(".data-table").forEach(function (table) {
    var titres = Array.prototype.map.call(table.querySelectorAll("thead th"), function (th) {
      return th.textContent.trim();
    });
    if (!titres.length) return;
    table.querySelectorAll("tbody tr").forEach(function (tr) {
      Array.prototype.forEach.call(tr.children, function (td, i) {
        if (!td.hasAttribute("data-label")) td.setAttribute("data-label", titres[i] || "");
        // regroupe le contenu de la cellule pour qu'il reste dans la colonne « valeur »
        if (td.childNodes.length > 1 && !td.querySelector(":scope > .cellule")) {
          var bloc = document.createElement("div");
          bloc.className = "cellule";
          while (td.firstChild) bloc.appendChild(td.firstChild);
          td.appendChild(bloc);
        }
      });
    });
    table.classList.add("cartes");
  });

  /* --- Afficher / masquer le mot de passe ---------------------------------- */
  document.querySelectorAll("[data-voir-mdp]").forEach(function (b) {
    b.addEventListener("click", function () {
      var champ = document.getElementById(b.getAttribute("data-voir-mdp"));
      if (!champ) return;
      var visible = champ.type === "text";
      champ.type = visible ? "password" : "text";
      b.setAttribute("aria-pressed", String(!visible));
      b.setAttribute("aria-label", visible ? "Afficher le mot de passe" : "Masquer le mot de passe");
      b.querySelector(".oeil-ouvert").hidden = !visible;
      b.querySelector(".oeil-ferme").hidden = visible;
    });
  });

  /* --- Bouton « en cours » à l'envoi d'un formulaire ------------------------ */
  document.querySelectorAll("form[data-chargement]").forEach(function (f) {
    f.addEventListener("submit", function () {
      var b = f.querySelector("button[type=submit]");
      if (!b) return;
      b.classList.add("chargement");
      b.setAttribute("aria-busy", "true");
      // évite le double envoi, sans bloquer un retour arrière du navigateur
      setTimeout(function () { b.disabled = true; }, 0);
    });
  });
  window.addEventListener("pageshow", function () {
    document.querySelectorAll("button.chargement").forEach(function (b) {
      b.classList.remove("chargement");
      b.disabled = false;
      b.removeAttribute("aria-busy");
    });
  });
})();
