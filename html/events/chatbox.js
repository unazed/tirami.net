window.in_chatbox = true;
window.ws.send(JSON.stringify({
  action: "initialize_chat"
}));
$("#chatbox").removeClass("d-none").css({
  width: "100%"
});
$("#main_container").addClass("d-none");
