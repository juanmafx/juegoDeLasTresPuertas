<?php

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use MontyHall\Lab\Cli;
use MontyHall\Lab\Fraction;
use MontyHall\Lab\Host;
use MontyHall\Lab\Scenario;
use MontyHall\Lab\ScenarioError;
use MontyHall\Lab\Solver;
use MontyHall\Lab\Tests\SpecData;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class SolverTest extends TestCase
{
    public static function scenarios(): array
    {
        return SpecData::list('scenarios.json', 'scenarios');
    }

    #[DataProvider('scenarios')]
    public function testMatchesSpecExpectation(array $entry): void
    {
        $report = Cli::exactReport(SpecData::scenario(SpecData::array($entry['scenario'])));
        $expected = SpecData::array(SpecData::array($entry['expected'])['exact']);
        self::assertSame($expected['prize_at_pick'], $report['prize_at_pick']);
        self::assertSame($expected['outcomes'], $report['outcomes']);
        self::assertSame($expected['win'], $report['win']);
    }

    public function testClassicGame(): void
    {
        $result = Solver::solve(new Scenario());
        self::assertSame('1/3', $result->stay?->toString());
        self::assertSame('2/3', $result->switch?->toString());
        self::assertSame('1/2', $result->mixed(Fraction::of(1, 2))?->toString());
    }

    public function testRandomHostMakesSwitchingWorthless(): void
    {
        $result = Solver::solve(new Scenario(host: Host::Random));
        self::assertSame('2/3', $result->decision->toString());
        self::assertSame('1/3', $result->void->toString());
        self::assertSame('1/2', $result->stay?->toString());
        self::assertSame('1/2', $result->switch?->toString());
    }

    public function testAdversarialHostOnlyOffersWhenPickWins(): void
    {
        $result = Solver::solve(new Scenario(host: Host::Adversarial));
        self::assertSame('1/3', $result->decision->toString());
        self::assertSame('2/3', $result->noOffer->toString());
        self::assertSame('1/1', $result->stay?->toString());
        self::assertSame('0/1', $result->switch?->toString());
    }

    public function testAdversarialHostWithZeroPriorPickHasNoDecision(): void
    {
        $result = Solver::solve(new Scenario(doors: 4, prior: [0, 1, 1, 1], host: Host::Adversarial));
        self::assertSame('0/1', $result->decision->toString());
        self::assertNull($result->stay);
        self::assertNull($result->mixed(Fraction::of(1, 2)));
    }

    public function testBiasedObservedRevealUsesHostWeights(): void
    {
        $result = Solver::solve(new Scenario(host: Host::Biased, hostWeights: [1, 1, 3], observed: [2]));
        self::assertSame('7/12', $result->observed?->toString());
        self::assertSame('3/7', $result->stay?->toString());
        self::assertSame('4/7', $result->switch?->toString());
    }

    public function testImpossibleObservationGivesNullWins(): void
    {
        $result = Solver::solve(new Scenario(doors: 4, prior: [0, 0, 0, 1], reveals: 1, observed: [3]));
        self::assertSame('0/1', $result->observed?->toString());
        self::assertNull($result->stay);
        self::assertNull($result->switch);
    }

    public function testSixtyFourDoorRandomHost(): void
    {
        $result = Solver::solve(new Scenario(doors: 64, prizes: 30, reveals: 25, host: Host::Random));
        self::assertSame('2431/18587252908392', $result->decision->toString());
        self::assertSame('10/13', $result->switch?->toString());
    }

    public function testEnumerationLimit(): void
    {
        $this->expectException(ScenarioError::class);
        Solver::solve(new Scenario(doors: 11, prior: array_fill(0, 11, 1)));
    }

    public function testBinomial(): void
    {
        self::assertSame('1', Solver::binomial(5, 0)->toString());
        self::assertSame('10', Solver::binomial(5, 2)->toString());
        self::assertSame('0', Solver::binomial(3, 4)->toString());
        self::assertSame('916312070471295267', Solver::binomial(63, 31)->toString());
    }
}
