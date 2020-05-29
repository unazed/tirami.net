var TYPES = {
  error: "rgba(220, 53, 69, 0.5)",
  info: "rgba(23, 162, 184, 0.5)",
  success: "rgba(40, 167, 69, 0.5)",
  warning: "rgba(253, 126, 20, 0.5)"
}

function is_mobile() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
}

String.prototype.toProperCase = function () {
    return this.replace(/\w\S*/g, function(txt){return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase();});
};

function reset_state() {
  if (window.in_chatbox !== undefined && window.in_chatbox) {
    $("#main_container").removeClass("d-none");
    if (is_mobile()) {
      $("#chatbox").removeClass("d-flex").addClass("d-none");
    } else {
      $("#chatbox").css({width: "27%"});
    }
  }
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
  var prev_msg = $(".message-content")[0];
  $("#chatbox-messages").prepend(
    $("<div></div>").addClass("chatbox-message").append(
      label_obj = $("<label></label>").addClass("message-content").text(
        message_obj.username?
          (message_obj.username + ": " + message_obj.content):
          (message_obj.content)
      )
    ).css(message_obj.properties === undefined? {}: message_obj.properties)
  );
  if (prev_msg !== undefined && prev_msg.textContent.startsWith(message_obj.username + ":")) {
    label_obj.parent().addClass("border-0");
  }
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
  $(".nav-link").each(function(idx, elem) {
    $(elem).off("click");
    $(elem).click(function() {
      if (window.ws === undefined) {
        display_notif("wait a moment for the websockets to initialize", "error");
        return;
      }
      if (this.name === "logout") {
        window.ws.send(JSON.stringify({
          action: "logout"
        }))
      } else {
        window.ws.send(JSON.stringify({
          action: "event_handler",
          name: $(this).attr('name'),
        }));
      }
      $(".nav-link.active").toggleClass("active");
      $(this).toggleClass("active");
    });
  });
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
    if (!is_mobile()) {
      $("#chatbox").removeClass("d-none").addClass("d-flex");
      ws.send(JSON.stringify({
        action: "initialize_chat"
      }));
    }
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

$("#chatbox_input").on("keypress", function(e) {
  if (e.which == 13) {
    $(this).attr("disabled", "disabled");
    if (!(msg = $(this).val())) {
      display_notif("message cannot be empty", "warning");
      setTimeout(function(obj) {
        obj.removeAttr("disabled");
      }, 500, $(this));
      return;
    }
    window.ws.send(JSON.stringify({
      action: "send_message",
      message: msg
    }));
    $(this).val("");
    setTimeout(function(obj) {
      obj.removeAttr("disabled");
      $("#chatbox_input:text:visible:first").focus()
    }, 250, $(this));
  }
});
