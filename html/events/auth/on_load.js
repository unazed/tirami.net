$("#main_container").empty();
$("#main_container").append(
  $("<p></p>").text("you're authenticated as " + $$username + "!")
);
