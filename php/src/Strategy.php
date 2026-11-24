<?php

// Player strategies of the shared model.

declare(strict_types=1);

namespace MontyHall\Lab;

enum Strategy: string
{
    case Stay = 'stay';
    case Switch = 'switch';
    case Mixed = 'mixed';
}
