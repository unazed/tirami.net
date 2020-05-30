var out = $("#service-output");
out.val(out.val() + (out.val()? "\n": "") + $$message);
out.scrollTop(out[0].scrollHeight - out.height());
