<?php

// Host policies of the shared model.

declare(strict_types=1);

namespace MontyHall\Lab;

enum Host: string
{
    case Informed = 'informed';
    case Random = 'random';
    case Biased = 'biased';
    case Adversarial = 'adversarial';
}
