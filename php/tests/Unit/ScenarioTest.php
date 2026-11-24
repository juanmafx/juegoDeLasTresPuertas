<?php

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use MontyHall\Lab\Fraction;
use MontyHall\Lab\Host;
use MontyHall\Lab\Scenario;
use MontyHall\Lab\ScenarioError;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class ScenarioTest extends TestCase
{
    public function testDefaultsAndEcho(): void
    {
        self::assertSame(
            [
                'doors' => 3,
                'prizes' => 1,
                'prior' => 'uniform',
                'pick' => 0,
                'reveals' => 1,
                'host' => 'informed',
                'host_weights' => null,
                'mixed' => '1/2',
                'observed' => null,
            ],
            (new Scenario())->toJson(),
        );
    }

    public function testObservedIsSorted(): void
    {
        $scenario = new Scenario(doors: 6, reveals: 3, observed: [5, 1, 3]);
        self::assertSame([1, 3, 5], $scenario->observed);
    }

    public function testWithRevealsDropsObservation(): void
    {
        $scenario = (new Scenario(doors: 5, reveals: 1, observed: [2]))->withReveals(3);
        self::assertSame(3, $scenario->reveals);
        self::assertNull($scenario->observed);
        self::assertSame(3, $scenario->maxReveals());
    }

    public static function invalid(): array
    {
        return [
            'too few doors' => [static fn () => new Scenario(doors: 2)],
            'too many doors' => [static fn () => new Scenario(doors: 65)],
            'too many prizes' => [static fn () => new Scenario(doors: 5, prizes: 4)],
            'too many reveals' => [static fn () => new Scenario(doors: 5, prizes: 2, reveals: 3)],
            'negative reveals' => [static fn () => new Scenario(reveals: -1)],
            'pick out of range' => [static fn () => new Scenario(pick: 3)],
            'observed pick' => [static fn () => new Scenario(observed: [0])],
            'observed wrong length' => [static fn () => new Scenario(observed: [1, 2])],
            'observed duplicate' => [static fn () => new Scenario(doors: 5, reveals: 2, observed: [1, 1])],
            'observed out of range' => [static fn () => new Scenario(observed: [3])],
            'biased without weights' => [static fn () => new Scenario(host: Host::Biased)],
            'weights without biased' => [static fn () => new Scenario(hostWeights: [1, 1, 1])],
            'zero host weight' => [static fn () => new Scenario(host: Host::Biased, hostWeights: [1, 0, 1])],
            'host weight too large' => [static fn () => new Scenario(host: Host::Biased, hostWeights: [1, 1_000_001, 1])],
            'short prior' => [static fn () => new Scenario(prior: [1, 1])],
            'negative prior' => [static fn () => new Scenario(prior: [1, -1, 1])],
            'prior with too few positive weights' => [static fn () => new Scenario(doors: 4, prizes: 2, prior: [0, 0, 0, 1])],
            'mixed above one' => [static fn () => new Scenario(mixed: Fraction::of(3, 2))],
            'mixed below zero' => [static fn () => new Scenario(mixed: Fraction::of(-1, 2))],
        ];
    }

    #[DataProvider('invalid')]
    public function testRejectsInvalidScenario(callable $build): void
    {
        $this->expectException(ScenarioError::class);
        $build();
    }
}
