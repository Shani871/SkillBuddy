"use strict";

// side navigation bar
function toggleSidebar() {
  document.getElementById("side-nav").classList.toggle("active");
  // Manage overlay for mobile
  let overlay = document.getElementById("sidebar-overlay");
  if (!overlay) {
    overlay = document.createElement("div");
    overlay.id = "sidebar-overlay";
    overlay.style.position = "fixed";
    overlay.style.top = "0";
    overlay.style.left = "0";
    overlay.style.width = "100%";
    overlay.style.height = "100%";
    overlay.style.backgroundColor = "rgba(0,0,0,0.5)";
    overlay.style.zIndex = "1040";
    overlay.onclick = toggleSidebar;
    document.body.appendChild(overlay);
  } else {
    overlay.remove();
  }
}

// #################################
// popup

var c = 0;
function pop() {
  if (c == 0) {
    document.getElementById("popup-box").style.display = "block";
    c = 1;
  } else {
    document.getElementById("popup-box").style.display = "none";
    c = 0;
  }
}

// const popupMessagesButtons = document.querySelectorAll('popup-btn-messages')

// popupMessagesButtons.forEach(button, () => {
//     button.addEventListener('click', () => {
//         document.getElementById('popup-box-messages').style.display = 'none';
//     })
// })

// const popupMessagesButtom = document.getElementById('popup-btn-messages')
// popupMessagesButtom.addEventListener('click', () => {
//     document.getElementById('popup-box-messages').style.display = 'none';
// })
// ##################################

// Example starter JavaScript for disabling form submissions if there are invalid fields
// Fetch all the forms we want to apply custom Bootstrap validation styles to
var forms = document.getElementsByClassName("needs-validation");

// Loop over them and prevent submission
Array.prototype.filter.call(forms, function (form) {
  form.addEventListener(
    "submit",
    function (event) {
      if (form.checkValidity() === false) {
        event.preventDefault();
        event.stopPropagation();
      }
      form.classList.add("was-validated");
    },
    false
  );
});
// ##################################

// extend and collapse
function showCourses(btn) {
  var btn = $(btn);

  if (collapsed) {
    btn.html('Collapse <i class="fas fa-angle-up"></i>');
    $(".hide").css("max-height", "unset");
    $(".white-shadow").css({ background: "unset", "z-index": "0" });
  } else {
    btn.html('Expand <i class="fas fa-angle-down"></i>');
    $(".hide").css("max-height", "150");
    $(".white-shadow").css({
      background: "linear-gradient(transparent 50%, rgba(255,255,255,.8) 80%)",
      "z-index": "2",
    });
  }
  collapsed = !collapsed;
}

document.addEventListener("DOMContentLoaded", function () {
  const topNavbar = document.getElementById("top-navbar");
  const searchInput = document.getElementById("primary-search");
  const helperPanel = document.getElementById("search-helper");
  const helperItems = helperPanel
    ? Array.from(helperPanel.querySelectorAll(".helper-item"))
    : [];

  if (!topNavbar || !searchInput) {
    return;
  }

  const filterHelperItems = function (value) {
    if (!helperItems.length) {
      return;
    }

    const query = value.trim().toLowerCase();
    helperItems.forEach(function (item) {
      const label = (item.dataset.searchLabel || item.textContent || "")
        .trim()
        .toLowerCase();
      const isVisible = query === "" || label.includes(query);
      item.classList.toggle("is-filtered-out", !isVisible);
    });
  };

  const activateSearchMode = function () {
    topNavbar.classList.add("search-active");
    if (helperPanel) {
      helperPanel.setAttribute("aria-hidden", "false");
    }
    filterHelperItems(searchInput.value);
  };

  const deactivateSearchMode = function () {
    topNavbar.classList.remove("search-active");
    if (helperPanel) {
      helperPanel.setAttribute("aria-hidden", "true");
    }
    helperItems.forEach(function (item) {
      item.classList.remove("is-filtered-out");
    });
  };

  searchInput.addEventListener("focus", activateSearchMode);
  searchInput.addEventListener("input", function () {
    activateSearchMode();
  });

  searchInput.addEventListener("blur", function () {
    setTimeout(function () {
      if (
        document.activeElement &&
        helperPanel &&
        helperPanel.contains(document.activeElement)
      ) {
        return;
      }
      deactivateSearchMode();
    }, 100);
  });

  helperItems.forEach(function (item) {
    item.addEventListener("mousedown", function () {
      deactivateSearchMode();
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && topNavbar.classList.contains("search-active")) {
      deactivateSearchMode();
      searchInput.blur();
    }
  });

  document.addEventListener("click", function (event) {
    if (!topNavbar.classList.contains("search-active")) {
      return;
    }
    if (!(event.target instanceof Element)) {
      return;
    }
    if (!event.target.closest(".search-container")) {
      deactivateSearchMode();
    }
  });
});
