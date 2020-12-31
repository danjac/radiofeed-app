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
const turboEventHandlers = {
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

const addListeners = (controller) => {
  const listeners = {};

  Object.keys(turboEventHandlers).forEach((eventName) => {
    const methodName = turboEventHandlers[eventName];
    if (typeof controller[methodName] === 'function') {
      listeners[eventName] = controller[methodName].bind(controller);
      document.documentElement.addEventListener(eventName, listeners[eventName], true);
    }
  });
  return listeners;
};

const removeListeners = (listeners) => {
  Object.keys(listeners).forEach((eventName) => {
    document.documentElement.removeEventListener(eventName, listeners[eventName], true);
  });
};

export default (controller) => {
  const listeners = addListeners(controller);

  const controllerDisconnect = controller.disconnect.bind(controller);

  Object.assign(controller, {
    disconnect() {
      removeListeners(listeners);
      controllerDisconnect();
    },
  });
};
