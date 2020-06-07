let TYPES = {
  "info": "#000",
  "error": "rgba(255, 0, 0, 0.5)",
};

function display_notif(message, type) {
  $("body").append(
    $("<div>").addClass("notif").append(
      $("<label>").text(message)
    ).css({"border": ("1px solid " + TYPES[type])})
     .fadeOut(4000, function() {
       $(this).remove();
     })
  );
}

function handle_ws_message(data) {
  console.log("got", data);
}

$(window).on("load", function() {
  if (window.WebSocket === undefined) {
    window.location.href = "unsupported?code=400";
    return;
  }
  window.ws = new WebSocket("wss://" + window.location.host + "/ws-registrar");

  window.ws.onerror = function() {
    display_notif("websocket raised error, disconnecting", "error");
  }

  window.ws.onclose = function() {
    display_notif("websocket terminating", "info");
  }

  window.ws.onopen = function() {
    display_notif("websocket opened", "info");
  }

  window.ws.onmessage = handle_ws_message;
});

$("#submit").click(function() {
  let username = $("#username").val();
  let password = $("#password").val();
  if (!username) {
    $("#username").css({
      "border": "2px solid rgba(255, 0, 0, 0.5)"
    });
    return;
  } else {
      $("#username").removeAttr('style');
  }

  if (!password) {
    $("#password").css({
      "border": "2px solid rgba(255, 0, 0, 0.5)"
    });
    return;
  } else {
    $("#password").removeAttr('style');
  }
  window.ws.send(JSON.stringify({
    "action": "login",
    "username": username,
    "password": password
  }));
});
