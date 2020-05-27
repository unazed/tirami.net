var TYPES = {
  error: "rgba(220, 53, 69, 0.5)",
  info: "rgba(23, 162, 184, 0.5)",
  success: "rgba(40, 167, 69, 0.5)",
  warning: "rgba(253, 126, 20, 0.5)"
}

function display_notif(message, type) {
  $("#error_div").append(
    $("<p></p>").text(message).prepend(
      $("<img width='16' height='16'></img>").attr(
        'src', "html/img/caret-down-fill.svg"
      ).click(function() {
        $(this).parent().fadeOut(1000, function() {
          this.remove();
        })
      }).on("load", function() {
        setTimeout(function(elem) {
          elem.parent().fadeOut(1000, function() {
            this.remove()
          });
        }, 2000, $(this));
      })
    ).css({
      borderLeft: "4px solid " + TYPES[type]
    })
  );
}

function add_message(message_obj) {
  console.log("got message", message_obj);
  $("#chatbox").append(
    $("<div></div>").addClass("chatbox-message").append(
      $("<label></label").addClass("chatbox-username").text(message_obj.username + ":"),
      $("<label></label>").addClass("chatbox-message").text(message_obj.content)
        .css(message_obj.properties === undefined? {}: message_obj.properties)
    )
  );
}

function handle_ws_message(event) {
  let content = JSON.parse(event.data);
  if (content.error) {
    display_notif(content.error, "error");
  } else if (content.action === "do_load") {
    jQuery.globalEval(content.data);
  } else if (content.action === "registered") {
    sessionStorage.setItem("token", content.data.token);
    sessionStorage.setItem("username", content.data.username);
    window.ws.send(JSON.stringify({
      action: "event_handler",
      name: "home"
    }));
  } else if (content.action === "login") {
    console.log(content);
    if (content.data.token === undefined && content.data.username) {
      window.sessionStorage.setItem("username", content.data.username);
    } else {
      window.sessionStorage.setItem("username", content.data.username);
      window.sessionStorage.setItem("token", content.data.token);
    }
    window.ws.send(JSON.stringify({
      action: "event_handler",
      name: "home"
    }));
  } else if (content.action === "on_message") {
    add_message(content.message);
  } else if (content.warning) {
    display_notif(content.warning, "warning");
  }
}

$(window).on("load", function() {
  if (window.WebSocket === undefined) {
    window.location.href = "unsupported?code=400";
    return;
  }
  window.ws = new WebSocket("wss://" + window.location.host + "/ws-tirami");
  window.ws.onerror = function() {
    display_notif("failed to connect to server websocket feed.", "error");
  }

  window.ws.onopen = function() {
    token = window.sessionStorage['token'];
    console.log(token);
    if (token) {
      ws.send(JSON.stringify({
        action: "login",
        token: token
      }))
    }
    ws.send(JSON.stringify({
      action: "event_handler",
      name: "home"
    }));
    ws.send(JSON.stringify({
      action: "initialize_chat"
    }));
    window.nav_update = setInterval(function() {
      ws.send(JSON.stringify({
        action: "event_handler",
        name: "navigation"
      }))
    }, 1000);
  }

  window.ws.onmessage = handle_ws_message;
  window.ws.onclose = function(event) {
    if (event.wasClean) {
      display_notif("closed websocket peacefully", "info");
    } else {
      display_notif("closed websocket abruptly", "error");
    }
    clearInterval(window.nav_update);
  }
});

$(".nav-link").each(function(idx, elem) {
  $(elem).click(function() {
    if (window.ws === undefined) {
      display_notif("wait a moment for the websockets to initialize", "error");
      return;
    }
    window.ws.send(JSON.stringify({
      action: "event_handler",
      name: $(this).attr('name'),
    }));
    $(".nav-link.active").toggleClass("active");
    $(this).toggleClass("active");
  });
});
