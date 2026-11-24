<?php

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use InvalidArgumentException;
use MontyHall\Lab\Wilson;
use PHPUnit\Framework\TestCase;

final class WilsonTest extends TestCase
{
    public function testSpecDocumentExample(): void
    {
        [$lower, $upper] = Wilson::interval(343, 675);
        self::assertEqualsWithDelta(0.4704943569066854, $lower, 1e-12);
        self::assertEqualsWithDelta(0.545709721169379, $upper, 1e-12);
    }

    public function testEdgesAreExact(): void
    {
        self::assertSame(0.0, Wilson::interval(0, 50)[0]);
        self::assertSame(1.0, Wilson::interval(50, 50)[1]);
        [$lower, $upper] = Wilson::interval(25, 50);
        self::assertEqualsWithDelta(1.0, $lower + $upper, 1e-12);
    }

    public function testRejectsEmptySample(): void
    {
        $this->expectException(InvalidArgumentException::class);
        Wilson::interval(0, 0);
    }

    public function testRejectsTooManySuccesses(): void
    {
        $this->expectException(InvalidArgumentException::class);
        Wilson::interval(3, 2);
    }
}
