reset_state();
$("#main_container").empty().append(
`<div class="input-group mb-3">
  <div class="input-group-prepend">
    <span class="input-group-text" id="basic-addon1">tirami.net/profile/</span>
  </div>
  <input type="text" id="input_username" class="form-control"
    placeholder="Username" aria-label="Username" aria-describedby="basic-addon1">
</div>
<div class="input-group mb-3">
  <input type="password" id="input_password" class="form-control"
    placeholder="Password">
</div>`);
var username = $("#input_username");
var password = $("#input_password");
var button = $('<button type="submit" class="btn btn-secondary">Login</button>');
$("#main_container").append(button);
if ($$username) {
  username.prop("disabled", true);
  password.prop("disabled", true);
  button.prop("disabled", true);
  display_notif("you're already logged in", "warning");
  setTimeout(function() {
    window.ws.send(JSON.stringify({
      action: "event_handler",
      name: "home"
    }))
  }, 2000);
} else {
  $(button).click(function() {
    window.ws.send(JSON.stringify({
      action: "login",
      username: username.val(),
      password: password.val()
    }));
    username.prop("disabled", true);
    password.prop("disabled", true);
  });
}
