<?php

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use MontyHall\Lab\Host;
use MontyHall\Lab\Scenario;
use MontyHall\Lab\ScenarioError;
use MontyHall\Lab\Simulator;
use MontyHall\Lab\Tests\SpecData;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class SimulatorTest extends TestCase
{
    public static function runs(): array
    {
        $scenarios = [];
        foreach (SpecData::list('scenarios.json', 'scenarios') as $id => [$entry]) {
            $scenarios[$id] = SpecData::array($entry)['scenario'];
        }
        $cases = [];
        foreach (SpecData::list('simulation-reference.json', 'runs') as $id => [$run]) {
            $cases[$id] = [SpecData::array($run), SpecData::array($scenarios[$id])];
        }
        return $cases;
    }

    #[DataProvider('runs')]
    public function testBitIdenticalToReference(array $run, array $scenario): void
    {
        $counts = Simulator::simulate(SpecData::scenario($scenario), SpecData::int($run['trials']), SpecData::int($run['seed']));
        self::assertSame(
            $run['counts'],
            ['decision' => $counts->decision, 'void' => $counts->void, 'no_offer' => $counts->noOffer, 'observed' => $counts->observed],
        );
        self::assertSame($run['sample_size'], $counts->sampleSize());
        self::assertSame($run['wins'], ['stay' => $counts->stayWins, 'switch' => $counts->switchWins, 'mixed' => $counts->mixedWins]);
    }

    public function testSpecDocumentExample(): void
    {
        $counts = Simulator::simulate(new Scenario(host: Host::Random), 1000, 1);
        self::assertSame([675, 325, 0], [$counts->decision, $counts->void, $counts->noOffer]);
        self::assertSame([343, 332, 346], [$counts->stayWins, $counts->switchWins, $counts->mixedWins]);
    }

    public function testObservationDoesNotChangeTheStream(): void
    {
        $plain = Simulator::simulate(new Scenario(doors: 4), 2000, 5);
        $observed = Simulator::simulate(new Scenario(doors: 4, observed: [2]), 2000, 5);
        self::assertSame($plain->decision, $observed->decision);
        self::assertNotNull($observed->observed);
        self::assertLessThan($plain->decision, $observed->observed);
        self::assertSame($observed->observed, $observed->sampleSize());
    }

    public function testAdversarialNeverWinsBySwitching(): void
    {
        $counts = Simulator::simulate(new Scenario(host: Host::Adversarial), 3000, 3);
        self::assertSame(3000, $counts->decision + $counts->noOffer);
        self::assertSame($counts->decision, $counts->stayWins);
        self::assertSame(0, $counts->switchWins);
    }

    public static function invalidRuns(): array
    {
        return [[0, 1], [100_000_001, 1], [10, -1]];
    }

    #[DataProvider('invalidRuns')]
    public function testRejectsInvalidRun(int $trials, int $seed): void
    {
        $this->expectException(ScenarioError::class);
        Simulator::simulate(new Scenario(), $trials, $seed);
    }
}
