/* Bottles Reference Widget
 *
 * Replicates senaite's reference widget UI (SearchField + SearchResults) for
 * the "Bottle" subfield inside BottlesWidget. A single text input is used for
 * both search and form submission; results appear in an inline dropdown panel
 * appended to <body> and positioned below the active input group.
 */
(function () {
  "use strict";

  var PANEL_ID = "bottles-results-panel";
  var activeWidget = null;
  var debounceTimer = null;
  var currentTerm = "";
  var currentPage = 1;
  var totalPages = 1;

  /* ── URL ── */

  function getBaseUrl() {
    var el = document.querySelector("input[name='portal_url']");
    if (el && el.value) return el.value.replace(/\/$/, "");
    if (window.portal_url) return String(window.portal_url).replace(/\/$/, "");
    /* Strip the last path segment (view name) from the current page URL */
    return window.location.href.replace(/\/[^/?#]*([?#].*)?$/, "");
  }

  /* ── Results panel (singleton appended to body) ── */

  function ensurePanel() {
    var panel = document.getElementById(PANEL_ID);
    if (panel) return panel;

    panel = document.createElement("div");
    panel.id = PANEL_ID;
    panel.className = "bottles-results-panel";
    panel.innerHTML =
      '<div class="bottles-results-loading" style="display:none">Loading&#8230;</div>' +
      '<table class="table table-sm table-hover small queryselectwidget-results-table mb-0">' +
        '<thead><tr class="bottles-results-thead"></tr></thead>' +
        '<tbody class="bottles-results-tbody"></tbody>' +
      '</table>' +
      '<nav class="bottles-results-pagination" style="display:none"></nav>';

    document.body.appendChild(panel);
    return panel;
  }

  function positionPanel(widget) {
    var panel = ensurePanel();
    var rect = widget.getBoundingClientRect();
    panel.style.top  = rect.bottom + "px";
    panel.style.left = rect.left + "px";
    panel.style.width = "550px";
  }

  function showPanel(widget) {
    activeWidget = widget;
    var panel = ensurePanel();
    positionPanel(widget);
    panel.style.display = "block";
  }

  function hidePanel() {
    var panel = document.getElementById(PANEL_ID);
    if (panel) panel.style.display = "none";
    activeWidget = null;
  }

  /* ── Pagination ── */

  function buildPageNumbers(current, total, padding) {
    var pages = [];
    var first = Math.max(1, current - padding);
    var last  = Math.min(total, current + padding);

    if (first > 1) {
      pages.push(1);
      if (first > 2) pages.push("...");
    }
    for (var p = first; p <= last; p++) pages.push(p);
    if (last < total) {
      if (last < total - 1) pages.push("...");
      pages.push(total);
    }
    return pages;
  }

  function renderPagination(total, current) {
    var panel = ensurePanel();
    var nav = panel.querySelector(".bottles-results-pagination");
    if (total <= 1) {
      nav.style.display = "none";
      nav.innerHTML = "";
      return;
    }

    var pages = buildPageNumbers(current, total, 3);
    var html = '<ul class="pagination pagination-sm justify-content-center mb-1 mt-1">';

    html += '<li class="page-item' + (current <= 1 ? " disabled" : "") + '">' +
            '<button class="page-link bottles-page-btn" data-page="' + (current - 1) + '">Previous</button></li>';

    pages.forEach(function (p) {
      if (p === "...") {
        html += '<li class="page-item disabled"><div class="page-link">&#8230;</div></li>';
      } else {
        html += '<li class="page-item' + (p === current ? " active" : "") + '">' +
                '<button class="page-link bottles-page-btn" data-page="' + p + '">' + p + '</button></li>';
      }
    });

    html += '<li class="page-item' + (current >= total ? " disabled" : "") + '">' +
            '<button class="page-link bottles-page-btn" data-page="' + (current + 1) + '">Next</button></li>';

    html += "</ul>";
    nav.innerHTML = html;
    nav.style.display = "block";
  }

  /* ── Fetch and render ── */

  function widgetData(widget) {
    var colModel = [];
    try { colModel = JSON.parse(widget.getAttribute("data-colmodel") || "[]"); }
    catch (e) { colModel = []; }
    return {
      url:       widget.getAttribute("data-url") || "",
      fieldName: widget.getAttribute("data-fieldname") || "",
      subfield:  widget.getAttribute("data-subfield") || "",
      colModel:  colModel
    };
  }

  function fetchResults(widget, term, page) {
    var d = widgetData(widget);
    if (!d.url) return;

    page = page || 1;
    currentTerm = term;
    currentPage = page;

    var panel = ensurePanel();
    var loading = panel.querySelector(".bottles-results-loading");
    var thead   = panel.querySelector(".bottles-results-thead");
    var tbody   = panel.querySelector(".bottles-results-tbody");

    loading.style.display = "block";
    tbody.innerHTML = "";
    showPanel(widget);

    var visibleCols = d.colModel.filter(function (c) { return !c.hidden; });
    thead.innerHTML = visibleCols.map(function (c) {
      return "<th class='border-top-0'>" + String(c.label || c.columnName || "") + "</th>";
    }).join("") + "<th class='border-top-0' style='width:1rem'></th>";

    var url = getBaseUrl() + "/" + d.url + "?page=" + page;
    if (term) url += "&SearchTerm=" + encodeURIComponent(term);

    fetch(url, { credentials: "same-origin" })
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.json();
      })
      .then(function (data) {
        loading.style.display = "none";
        totalPages = data.total || 1;

        var rows = data.rows || [];
        var span = visibleCols.length + 1;
        if (!rows.length) {
          tbody.innerHTML =
            '<tr><td colspan="' + span + '" class="text-center text-muted py-2">No results found</td></tr>';
          renderPagination(0, 1);
          return;
        }
        rows.forEach(function (row) {
          var tr = document.createElement("tr");
          tr.style.cursor = "pointer";
          tr.innerHTML = visibleCols.map(function (c) {
            var v = row[c.columnName];
            return "<td>" + (v != null ? String(v) : "") + "</td>";
          }).join("") + "<td></td>";
          /* mousedown fires before input blur, so the panel stays open long enough */
          tr.addEventListener("mousedown", function (e) {
            e.preventDefault();
            selectRow(widget, row, d);
          });
          tbody.appendChild(tr);
        });

        renderPagination(totalPages, currentPage);
      })
      .catch(function (err) {
        loading.style.display = "none";
        var span = visibleCols.length + 1;
        tbody.innerHTML =
          '<tr><td colspan="' + span + '" class="text-danger py-2">Error: ' + err.message + '</td></tr>';
        renderPagination(0, 1);
      });
  }

  /* ── Selection ── */

  function findInput(rowEl, fieldName, columnName) {
    return rowEl.querySelector(
      "input[name='" + fieldName + "." + columnName + ":records:ignore_empty']"
    );
  }

  function selectRow(widget, row, d) {
    var tableRow = widget.closest("tr");
    if (!tableRow) return;

    var searchInput = widget.querySelector(".bottles-ref-input");
    if (searchInput && row[d.subfield] != null) {
      searchInput.value = String(row[d.subfield]);
    }

    /* Update all companion inputs that match colModel columnNames */
    d.colModel.forEach(function (col) {
      var val = row[col.columnName];
      if (val == null) return;
      var input = findInput(tableRow, d.fieldName, col.columnName);
      if (input) input.value = String(val);
    });

    /* Dispatch blur on the form input so volume recalculation runs */
    var formInput = findInput(tableRow, d.fieldName, d.subfield);
    if (formInput) formInput.dispatchEvent(new Event("blur", { bubbles: true }));

    hidePanel();
  }

  /* ── Clear ── */

  function clearWidget(widget) {
    var d = widgetData(widget);
    var tableRow = widget.closest("tr");

    var searchInput = widget.querySelector(".bottles-ref-input");
    if (searchInput) searchInput.value = "";

    if (tableRow) {
      var formInput = findInput(tableRow, d.fieldName, d.subfield);
      if (formInput) formInput.value = "";

      ["container_uid", "DryWeight"].forEach(function (key) {
        var el = findInput(tableRow, d.fieldName, key);
        if (el) el.value = "";
      });

      if (formInput) formInput.dispatchEvent(new Event("blur", { bubbles: true }));
    }

    hidePanel();
  }

  /* ── Event wiring (all delegated so dynamically-added rows work) ── */

  document.addEventListener("DOMContentLoaded", function () {

    /* Focus on search input → show results */
    document.addEventListener("focus", function (e) {
      var input = e.target;
      if (!input || !input.classList.contains("bottles-ref-input")) return;
      var widget = input.closest(".bottles-ref-widget");
      if (!widget) return;
      clearTimeout(debounceTimer);
      fetchResults(widget, input.value, 1);
    }, true /* capture phase so focus is caught */);

    /* Typing → debounced fetch (reset to page 1) */
    document.addEventListener("input", function (e) {
      var input = e.target;
      if (!input || !input.classList.contains("bottles-ref-input")) return;
      var widget = input.closest(".bottles-ref-widget");
      if (!widget) return;
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(function () {
        fetchResults(widget, input.value, 1);
      }, 300);
    });

    /* Click events: search button, clear button, page buttons, outside-click */
    document.addEventListener("click", function (e) {
      /* Pagination page button */
      var pageBtn = e.target.closest(".bottles-page-btn");
      if (pageBtn) {
        e.preventDefault();
        var page = parseInt(pageBtn.getAttribute("data-page"), 10);
        if (activeWidget && page >= 1 && page <= totalPages) {
          fetchResults(activeWidget, currentTerm, page);
        }
        return;
      }

      /* Search button */
      var searchBtn = e.target.closest(".bottles-ref-search");
      if (searchBtn) {
        e.preventDefault();
        var widget = searchBtn.closest(".bottles-ref-widget");
        if (!widget) return;
        var val = (widget.querySelector(".bottles-ref-input") || {}).value || "";
        fetchResults(widget, val, 1);
        return;
      }

      /* Clear button */
      var clearBtn = e.target.closest(".bottles-ref-clear");
      if (clearBtn) {
        e.preventDefault();
        var widget = clearBtn.closest(".bottles-ref-widget");
        if (widget) clearWidget(widget);
        return;
      }

      /* Click outside both panel and any widget → hide */
      var panel = document.getElementById(PANEL_ID);
      if (panel && !panel.contains(e.target) && !e.target.closest(".bottles-ref-widget")) {
        hidePanel();
      }
    });

    /* Escape key → hide */
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") hidePanel();
    });

    /* Close on scroll — fixed positioning doesn't track the input */
    document.addEventListener("scroll", function () {
      hidePanel();
    }, true);
  });
})();
