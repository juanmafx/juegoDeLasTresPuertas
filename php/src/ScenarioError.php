<?php

// Invalid scenario or command-line input; the CLI maps it to exit code 2.

declare(strict_types=1);

namespace MontyHall\Lab;

use InvalidArgumentException;

final class ScenarioError extends InvalidArgumentException
{
}
