<?php

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use MontyHall\Lab\Cli;
use MontyHall\Lab\Fraction;
use MontyHall\Lab\Host;
use MontyHall\Lab\Optimum;
use MontyHall\Lab\Scenario;
use MontyHall\Lab\ScenarioError;
use MontyHall\Lab\Strategy;
use MontyHall\Lab\Tests\SpecData;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class OptimumTest extends TestCase
{
    public static function scenarios(): array
    {
        return array_filter(
            SpecData::list('scenarios.json', 'scenarios'),
            static fn (array $case): bool => is_array($case[0]) && isset($case[0]['optimum']),
        );
    }

    #[DataProvider('scenarios')]
    public function testMatchesSpecExpectation(array $entry): void
    {
        $request = SpecData::array($entry['optimum']);
        $report = Cli::optimumReport(
            SpecData::scenario(SpecData::array($entry['scenario'])),
            Strategy::from(SpecData::string($request['strategy'])),
            Fraction::parse(SpecData::string($request['cost'])),
        );
        $expected = SpecData::array(SpecData::array($entry['expected'])['optimum']);
        self::assertSame($expected['curve'], $report['curve']);
        self::assertSame($expected['optimum'], $report['optimum']);
        self::assertSame($expected['parabola'], $report['parabola']);
    }

    public function testSpecDocumentExample(): void
    {
        $report = Cli::optimumReport(new Scenario(doors: 5), Strategy::Switch, Fraction::of(1, 20));
        self::assertSame(['reveals' => 3, 'value' => '13/20'], $report['optimum']);
        self::assertSame(
            [
                'a' => '1/12',
                'b' => '-8/75',
                'c' => '21/100',
                'shape' => 'convex',
                'residual_sum_of_squares' => '1/500',
                'vertex' => ['reveals' => '16/25', 'value' => '1319/7500'],
                'vertex_offset' => '-59/25',
                'vertex_value_gap' => '-889/1875',
                'rounded_vertex' => ['reveals' => 1, 'value' => '13/60', 'regret' => '13/30'],
                'fitted_choice' => ['reveals' => 3, 'value' => '13/20', 'regret' => '0/1'],
            ],
            $report['parabola'],
        );
    }

    public function testExactQuadraticIsRecovered(): void
    {
        [$a, $b, $c] = Optimum::fitParabola([
            [0, Fraction::of(1)],
            [1, Fraction::of(5, 2)],
            [2, Fraction::of(3)],
            [3, Fraction::of(5, 2)],
        ]);
        self::assertSame(['-1/2', '2/1', '1/1'], [$a->toString(), $b->toString(), $c->toString()]);
    }

    public function testStayCurveIsLinearAndHasNoVertex(): void
    {
        $result = Optimum::curve(new Scenario(doors: 6), Strategy::Stay, Fraction::of(1, 10));
        $fit = $result->parabola;
        self::assertNotNull($fit);
        self::assertSame('linear', $fit->shape());
        self::assertNull($fit->vertexReveals);
        self::assertNull($fit->roundedVertex);
        self::assertSame(0, $result->best->reveals);
        self::assertSame('0/1', $fit->residualSumOfSquares->toString());
        self::assertSame('1/6', $fit->at(Fraction::zero())->toString());
    }

    public function testTiesGoToSmallestReveals(): void
    {
        $result = Optimum::curve(new Scenario(doors: 6), Strategy::Stay, Fraction::zero());
        self::assertSame(0, $result->best->reveals);
        self::assertSame(0, $result->parabola?->fittedChoice);
    }

    public function testFewerThanThreePointsHasNoParabola(): void
    {
        self::assertNull(Optimum::curve(new Scenario(), Strategy::Switch, Fraction::zero())->parabola);
    }

    public function testSixtyFourDoorCurve(): void
    {
        $result = Optimum::curve(new Scenario(doors: 64, prizes: 2, host: Host::Random), Strategy::Switch, Fraction::of(1, 1000));
        self::assertCount(62, $result->curve);
        self::assertSame(61, $result->best->reveals);
        self::assertSame('1817/3000', $result->best->value->toString());
        self::assertSame('34456544676421767777578692939/166929778611936622453844197324800', $result->parabola?->a->toString());
    }

    public function testRejectsNegativeCost(): void
    {
        $this->expectException(ScenarioError::class);
        Optimum::curve(new Scenario(), Strategy::Switch, Fraction::of(-1, 2));
    }

    public function testRejectsUndefinedDecision(): void
    {
        $this->expectException(ScenarioError::class);
        Optimum::curve(new Scenario(doors: 4, prior: [0, 1, 1, 1], host: Host::Adversarial), Strategy::Stay, Fraction::zero());
    }

    public function testRejectsObservation(): void
    {
        $this->expectException(ScenarioError::class);
        Optimum::curve(new Scenario(observed: [1]), Strategy::Stay, Fraction::zero());
    }
}
