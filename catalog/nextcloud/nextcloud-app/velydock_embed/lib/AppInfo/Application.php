<?php

declare(strict_types=1);

namespace OCA\VelydockEmbed\AppInfo;

use OCA\VelydockEmbed\Listener\FrameAncestorsListener;
use OCP\AppFramework\App;
use OCP\AppFramework\Bootstrap\IBootContext;
use OCP\AppFramework\Bootstrap\IBootstrap;
use OCP\AppFramework\Bootstrap\IRegistrationContext;
use OCP\Security\CSP\AddContentSecurityPolicyEvent;

class Application extends App implements IBootstrap {
	public const APP_ID = 'velydock_embed';

	public function __construct() {
		parent::__construct(self::APP_ID);
	}

	public function register(IRegistrationContext $context): void {
		$context->registerEventListener(AddContentSecurityPolicyEvent::class, FrameAncestorsListener::class);
	}

	public function boot(IBootContext $context): void {
	}
}
