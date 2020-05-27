username = $("#input_username");
password = $("#input_password");

if ($$object !== null) {
  $$object.addClass("is-invalid");
}
display_notif($$reason, "error");

username.prop("disabled", false);
password.prop("disabled", false);
