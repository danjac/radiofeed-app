const turboEventHandlers = {
  'turbo:beforeCache': 'turboBeforeCache',
  'turbo:beforeFetchRequest': 'turboBeforeVisit',
  'turbo:beforeFetchResponse': 'turboBeforeFetchResponse',
  'turbo:beforeRender': 'turboBeforeRender',
  'turbo:beforeVisit': 'turboBeforeVisit',
  'turbo:click': 'turboClick',
  'turbo:load': 'turboLoad',
  'turbo:render': 'turboRender',
  'turbo:submitEnd': 'turboSubmitEnd',
  'turbo:submitSubmitStart': 'turboSubmitStart',
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
};

const removeListeners = (listeners) => {
  Object.keys(listeners).forEach((eventName) => {
    document.documentElement.removeEventListener(eventName, listeners[eventName], true);
  });
};

export const useTurbo = (controller) => {
  const listeners = addListeners(controller);

  const controllerDisconnect = controller.disconnect.bind(controller);

  Object.assign(controller, {
    disconnect() {
      removeListeners(listeners);
      controllerDisconnect();
    },
  });
};
