/* CurrentKoi — interaction states.
 *
 * A submit is acknowledged in place: the control that fired it takes the
 * loading state and shows a spinner while the server answers. Everything else
 * (hover, focus, press) is pure CSS; this file only owns the loading handoff.
 */
(function () {
  "use strict";

  var LOADING = "is-loading";

  function submitterFor(form, event) {
    if (event && event.submitter) return event.submitter;
    return form.querySelector('[type="submit"], button:not([type])');
  }

  function beginLoading(control) {
    if (!control || control.hasAttribute("data-no-loading")) return;
    if (control.classList.contains(LOADING)) return;

    control.classList.add(LOADING);
    control.setAttribute("aria-busy", "true");
    control.setAttribute("aria-disabled", "true");

    // Disabling drops the button's own value from the POST; skip it when named.
    if (control.tagName === "BUTTON" && !control.name) {
      control.disabled = true;
    }
  }

  function endLoading(control) {
    control.classList.remove(LOADING);
    control.removeAttribute("aria-busy");
    control.removeAttribute("aria-disabled");
    if (control.tagName === "BUTTON") control.disabled = false;
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!(form instanceof HTMLFormElement)) return;
    if (form.hasAttribute("data-no-loading")) return;

    // A confirm() that the visitor dismissed, or a guarded resubmit, cancels
    // the default before it reaches us — never leave the button stuck.
    if (event.defaultPrevented) return;

    if (form.dataset.submitting === "true") {
      event.preventDefault();
      return;
    }
    form.dataset.submitting = "true";

    beginLoading(submitterFor(form, event));
  });

  // Controls that navigate can opt in with [data-loading].
  document.addEventListener("click", function (event) {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey) return;
    var control = event.target.closest("[data-loading]");
    if (control) beginLoading(control);
  });

  // Back/forward cache: a page restored mid-submit must not stay stuck.
  window.addEventListener("pageshow", function () {
    document.querySelectorAll("." + LOADING).forEach(endLoading);
    document.querySelectorAll("form[data-submitting]").forEach(function (form) {
      delete form.dataset.submitting;
    });
  });
})();
