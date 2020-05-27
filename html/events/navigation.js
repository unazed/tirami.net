if ($$username && !$("a#nav-username").get().length) {
  $(".navbar-nav.mr-auto").append(
    $("<li></li>").addClass("nav-item").append(
      $("<a></a>").addClass("nav-link").text($$username).attr({
        id: "nav-username",
        href: "#"
      }).click(function() {
        // on-click username
      })
    )
  ).append(
    $("<li></li>").addClass("nav-item").append(
      $("<a></a>").addClass("nav-link").text("logout").click(function() {
        window.ws.send(JSON.stringify({
          action: "logout"
        }))
      }).attr({
        id: "nav-logout",
        href: "#"
      })
    )
  );
  $("#nav-login").parent().hide();
  $("#nav-register").parent().hide();
} else if (!$$username && (nav = $("a#nav-username")).get().length) {
  nav.parent().remove();
  $("a#nav-logout").parent().remove();
  $("#nav-login").parent().show();
  $("#nav-register").parent().show();
  display_notif("logged out", "warning");
}
