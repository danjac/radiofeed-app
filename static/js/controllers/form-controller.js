import axios from "axios";
import Turbolinks from "turbolinks";

import { Controller } from "stimulus";

export default class extends Controller {
  async submit(event) {
    event.preventDefault();

    const referrer = location.href;
    const method = this.element.getAttribute("method");
    const url = this.element.getAttribute("action");

    const data = new FormData(this.element);

    const response = await axios({
      data,
      headers: {
        "Turbolinks-Referrer": referrer,
      },
      method,
      url,
    });
    const contentType = response.headers["content-type"];

    if (contentType.match(/html/)) {
      // errors in form, re-render
      Turbolinks.controller.cache.put(
        referrer,
        Turbolinks.Snapshot.wrap(response.data)
      );
      Turbolinks.visit(referrer, {
        action: "restore",
      });
    } else if (contentType.match(/javascript/)) {
      /* eslint-disable-next-line no-eval */
      eval(response.data);
    }
  }
}
