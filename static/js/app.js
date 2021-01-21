import '@hotwired/turbo';
import 'form-request-submit-polyfill';
import { Application } from 'stimulus';

import ConfirmController from './controllers/confirm-controller';
import DebounceController from './controllers/debounce-controller';
import EpisodeController from './controllers/episode-controller';
import LinkController from './controllers/link-controller';
import NotificationController from './controllers/notification-controller';
import PlayerController from './controllers/player-controller';
import ToggleController from './controllers/toggle-controller';

// Stimulus setup
const application = Application.start();

application.register('confirm', ConfirmController);
application.register('debounce', DebounceController);
application.register('episode', EpisodeController);
application.register('link', LinkController);
application.register('notification', NotificationController);
application.register('player', PlayerController);
application.register('toggle', ToggleController);
