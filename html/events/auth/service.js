reset_state();
$("#main_container").empty().append(
  $("<div>").prop("id", "service-container").append(
    $("<div>").prop("id", "service-subcontainer").append(
      $("<textarea>").prop({
        placeholder: "usernames (line-separated)",
        id: "service-username"
      }).addClass("form-control"),
      $("<button>").html("Check " + $$service.toProperCase() + " usernames").addClass("form-control")
    ).addClass("d-flex flex-column"),
    $("<textarea>").prop({
      placeholder: "checker output",
      id: "service-output",
      disabled: "disabled"
    }).addClass("form-control")
  ).addClass("d-flex border")
);
