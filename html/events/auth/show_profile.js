reset_state();
function on_results(resp) {
  results = $("#results");
  results.empty();
  if (jQuery.isEmptyObject(resp)) {
    results.append(
      $("<li>").addClass("list-group-item bg-transparent").append(
        $("<p>").addClass("p-2").text("No results found, maybe try run a check")
      )
    );
    return;
  }
  for (const id in resp) {
    obj = resp[id];
    results.append(
      $("<li>").addClass("list-group-item bg-transparent").append(
        $("<a>").text("Task #" + id + " for " + obj.service.toProperCase() +
                      " scheduled " + (obj.started << 0) + " seconds ago")
                .addClass("list-group-item-action ")
                .css({
                  "text-decoration": "none"
                })
                .click(function() {
                  var usernames = $($(this).parent().children("ul")[0]);
                  if (usernames.html()) {
                    usernames.empty();
                    return;
                  }
                  $.each(resp[id].result, function(username, is_taken) {
                    usernames.append(
                      $("<p>").text(username)
                              .css({
                                "border-left": "1em solid " +
                                    (is_taken? "#dc3545": "#20c997"),
                                "margin": "0",
                                "padding": "0",
                                "padding-left": "1em"
                              })
                    )
                  });
                }),
        $("<ul>")
      )
    );
  }
}

function on_profile(resp) {
  console.log(resp);
}

window.ws.send(JSON.stringify({
  action: "service_results"
}));

window.ws.send(JSON.stringify({
  action: "profile_info"
}));

$("#main_container").empty().append(
  $("<div>").addClass("d-flex flex-row border").append(
    $("<ul>").addClass("list-group flex-grow").prop("id", "results").append(
      $("<li>").addClass("list-group-item bg-transparent").append(
        $("<p>").addClass("p-2").text("Loading checks")
      )
    ).css({"margin": "1em", "flex-grow": "1"}),
    $("<ul>").addClass("list-group flex-grow").prop("id", "profile-info").append(
      $("<li>").addClass("list-group-item bg-transparent").append(
        $("<p>").addClass("p-2").text("Loading profile")
      )
    ).css({"margin": "1em", "margin-left": "0"})
  )
);
