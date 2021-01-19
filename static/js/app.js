import { Application } from 'stimulus';
import '@hotwired/turbo';

import ConfirmController from './controllers/confirm-controller';
import LinkController from './controllers/link-controller';
import NotificationController from './controllers/notification-controller';
import PlayerController from './controllers/player-controller';
import SocketController from './controllers/socket-controller';
import ToggleController from './controllers/toggle-controller';

// Stimulus setup
const application = Application.start();

application.register('confirm', ConfirmController);
application.register('link', LinkController);
application.register('notification', NotificationController);
application.register('player', PlayerController);
application.register('socket', SocketController);
application.register('toggle', ToggleController);
