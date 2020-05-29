reset_state();
$("#main_container").empty();
$("#main_container").append(`
  <p class="p-2 text-justify">
    Welcome to <strong>Tirami.net</strong>, we currently support mass
    username checking for the following services:
  </p>
  <ul class="service-item list-group list-group-flush">
    <li class="list-group-item bg-transparent">
      <a class="list-group-item-action" name="service/twitch.tv">twitch.tv</a>
      <object class="service-ico" type="image/svg+xml" data="html/img/twitch.svg"
        width="16" height="16">
      </object>
    </li>
    <li class="service-item list-group-item bg-transparent">
      <a class="list-group-item-action" name="service/snapchat">Snapchat</a>
      <object class="service-ico" type="image/svg+xml" data="html/img/snapchat.svg"
        width="16" height="16">
      </object>
    </li>
    <li class="service-item list-group-item bg-transparent">
      <a class="list-group-item-action" name="service/tiktok">TikTok</a>
      <object class="service-ico" type="image/svg+xml" data="html/img/tiktok.svg"
        width="16" height="16">
      </object>
    </li>
  </ul>`);

$(".service-item a").each(function(idx, elem) {
  $(elem).click(function() {
    window.ws.send(JSON.stringify({
      action: "event_handler",
      name: elem.name.toLowerCase()
    }));
  });
});
