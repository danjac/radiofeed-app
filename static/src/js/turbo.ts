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

const turboEventHandlers: any = {
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
  const listeners: any = {};

  Object.keys(turboEventHandlers).forEach((eventName: string) => {
    const methodName: string = turboEventHandlers[eventName];
    if (typeof controller[methodName] === 'function') {
      listeners[eventName] = controller[methodName].bind(controller);
      document.documentElement.addEventListener(eventName, listeners[eventName], true);
    }
  });
  return listeners;
};

const removeListeners = (listeners: any) => {
  Object.keys(listeners).forEach((eventName: string) => {
    document.documentElement.removeEventListener(eventName, listeners[eventName], true);
  });
};

export default (controller: Controller) => {
  const listeners: any = addListeners(controller);

  const controllerDisconnect: Function = controller.disconnect.bind(controller);

  Object.assign(controller, {
    disconnect() {
      removeListeners(listeners);
      controllerDisconnect();
    },
  });
};
