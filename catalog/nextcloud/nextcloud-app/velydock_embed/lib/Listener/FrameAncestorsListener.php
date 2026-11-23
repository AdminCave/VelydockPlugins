<?php

declare(strict_types=1);

namespace OCA\VelydockEmbed\Listener;

use OCA\VelydockEmbed\AppInfo\Application;
use OCP\AppFramework\Http\EmptyContentSecurityPolicy;
use OCP\EventDispatcher\Event;
use OCP\EventDispatcher\IEventListener;
use OCP\IAppConfig;
use OCP\Security\CSP\AddContentSecurityPolicyEvent;

/** @template-implements IEventListener<AddContentSecurityPolicyEvent> */
class FrameAncestorsListener implements IEventListener {
	public function __construct(
		private IAppConfig $appConfig,
	) {
	}

	public function handle(Event $event): void {
		if (!$event instanceof AddContentSecurityPolicyEvent) {
			return;
		}
		$value = $this->appConfig->getValueString(Application::APP_ID, 'frame_ancestors', '');
		$policy = new EmptyContentSecurityPolicy();
		$added = false;
		foreach (preg_split('/\s+/', trim($value)) ?: [] as $origin) {
			// Only plain https origins; anything else would widen the policy unexpectedly.
			if (preg_match('#^https://[a-z0-9.-]+(:[0-9]+)?$#', $origin) === 1) {
				$policy->addAllowedFrameAncestorDomain($origin);
				$added = true;
			}
		}
		if ($added) {
			$event->addPolicy($policy);
		}
	}
}
