/* Webbplatsens skript. Laddas i <head> utan defer, så att klassen "js" finns
   innan sidan ritas. Det övriga väntar tills sidan är inläst. Skripten ligger
   i en egen fil eftersom webbplatsens innehållspolicy inte tillåter inbäddade
   skript. */
document.documentElement.classList.add("js");

/* Menyn fälls ihop till en knapp på smala skärmar. Utan skript visas den som vanligt. */
function fornmedMeny() {
  var knapp = document.querySelector(".menyknapp");
  if (!knapp) return;
  knapp.hidden = false;
  knapp.addEventListener("click", function () {
    var oppen = knapp.getAttribute("aria-expanded") === "true";
    knapp.setAttribute("aria-expanded", oppen ? "false" : "true");
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && knapp.getAttribute("aria-expanded") === "true") {
      knapp.setAttribute("aria-expanded", "false");
      knapp.focus();
    }
  });
}

/* Källkritisk hjälp i träfflistan: slås på och av utan ny sidladdning. Valet
   sparas i adressen, så att det följer med länkar, och i webbläsaren, så att
   det gäller nästa sökning också. Utan skript används länken i noscript. */
function fornmedTextkritik() {
  var knapp = document.getElementById("textkritik-vaxel");
  var sok = document.querySelector(".sok");
  if (!knapp || !sok) return;
  function satt(pa) {
    sok.classList.toggle("med-textkritik", pa);
    knapp.setAttribute("aria-pressed", pa ? "true" : "false");
    knapp.querySelector(".vaxel-lage").textContent = pa ? "På" : "Av";
    var url = new URL(window.location.href);
    if (pa) { url.searchParams.set("textkritik", "1"); } else { url.searchParams.delete("textkritik"); }
    window.history.replaceState(null, "", url);
    document.querySelectorAll('.sok a[href^="?"]').forEach(function (a) {
      var u = new URL(a.getAttribute("href"), window.location.href);
      if (pa) { u.searchParams.set("textkritik", "1"); } else { u.searchParams.delete("textkritik"); }
      a.setAttribute("href", u.search);
    });
    var dolt = document.querySelector('.sokformular input[name="textkritik"]');
    if (pa && !dolt) {
      dolt = document.createElement("input");
      dolt.type = "hidden"; dolt.name = "textkritik"; dolt.value = "1";
      document.querySelector(".sokformular").appendChild(dolt);
    } else if (!pa && dolt) { dolt.remove(); }
    try { window.localStorage.setItem("fornmed-textkritik", pa ? "1" : "0"); } catch (e) {}
  }
  knapp.hidden = false;
  var sparat = null;
  try { sparat = window.localStorage.getItem("fornmed-textkritik"); } catch (e) {}
  if (sparat === "1" && knapp.getAttribute("aria-pressed") === "false") { satt(true); }
  knapp.addEventListener("click", function () { satt(knapp.getAttribute("aria-pressed") !== "true"); });
}

document.addEventListener("DOMContentLoaded", function () {
  fornmedMeny();
  fornmedTextkritik();
});
