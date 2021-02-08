// Turbo event handlers.
//
// 1) in your controller connect() method:
// connect() {
//    useTurbo(this)
// }
//
// 2) add specific handler:
// turboOnLoad(event) {
//  console.log(event)
// }
//
import { Controller } from 'stimulus';

const turboEventHandlers: Object = {
  'turbo:before-cache': 'turboBeforeCache',
  'turbo:before-fetch-request': 'turboBeforeVisit',
  'turbo:before-fetch-response': 'turboBeforeFetchResponse',
  'turbo:before-render': 'turboBeforeRender',
  'turbo:before-visit': 'turboBeforeVisit',
  'turbo:click': 'turboClick',
  'turbo:load': 'turboLoad',
  'turbo:render': 'turboRender',
  'turbo:submit-end': 'turboSubmitEnd',
  'turbo:submit-start': 'turboSubmitStart',
};

const addListeners = (controller: Controller): Object => {
  const listeners: Object = {};

  Object.keys(turboEventHandlers).forEach((eventName: String) => {
    const methodName: String = turboEventHandlers[eventName];
    if (typeof controller[methodName] === 'function') {
      listeners[eventName] = controller[methodName].bind(controller);
      document.documentElement.addEventListener(eventName, listeners[eventName], true);
    }
  });
  return listeners;
};

const removeListeners = (listeners: Object) => {
  Object.keys(listeners).forEach((eventName: String) => {
    document.documentElement.removeEventListener(eventName, listeners[eventName], true);
  });
};

export default (controller: Controller) => {
  const listeners: Object = addListeners(controller);

  const controllerDisconnect: Function = controller.disconnect.bind(controller);

  Object.assign(controller, {
    disconnect() {
      removeListeners(listeners);
      controllerDisconnect();
    },
  });
};
