<?php

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use MontyHall\Lab\Cli;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;
use RuntimeException;

final class CliTest extends TestCase
{
    public static function invalidInvocations(): array
    {
        $cases = [
            ['exact', '--doors', '2'],
            ['exact', '--doors', '65'],
            ['exact', '--doors', '5', '--prizes', '4'],
            ['exact', '--doors', '5', '--prizes', '2', '--reveals', '3'],
            ['exact', '--pick', '3'],
            ['exact', '--observed', '0'],
            ['exact', '--observed', '1,2'],
            ['exact', '--host', 'biased'],
            ['exact', '--host-weights', '1,1,1'],
            ['exact', '--host', 'biased', '--host-weights', '1,0,1'],
            ['exact', '--prior', '1,1'],
            ['exact', '--doors', '4', '--prizes', '2', '--prior', '0,0,0,1'],
            ['exact', '--mixed', '3/2'],
            ['exact', '--mixed', '1/0'],
            ['exact', '--doors', '11', '--prior', '1,1,1,1,1,1,1,1,1,1,1'],
            ['exact', '--doors', '11', '--observed', '1'],
            ['exact', '--doors', 'three'],
            ['exact', '--doors'],
            ['exact', '--host', 'oracle'],
            ['exact', '--unknown', '1'],
            ['exact', 'stray'],
            ['simulate', '--seed', '-1'],
            ['simulate', '--seed', '9223372036854775808'],
            ['simulate', '--seed', '1', '--trials', '0'],
            ['simulate', '--trials', '10'],
            ['optimum', '--strategy', 'switch', '--cost', '-1/2'],
            ['optimum', '--strategy', 'switch', '--reveals', '1'],
            ['optimum', '--strategy', 'gamble'],
            ['optimum'],
            ['optimum', '--strategy', 'stay', '--doors', '4', '--prior', '0,1,1,1', '--host', 'adversarial'],
            ['prng', '--seed', '1', '--kind', 'bounded', '--bound', '0'],
            ['prng', '--seed', '1', '--kind', 'bounded'],
            ['prng', '--seed', '1', '--kind', 'dice'],
            ['prng', '--seed', '1', '--kind', 'words', '--count', '0'],
            ['prng', '--seed', '1', '--kind', 'shuffle', '--size', '10001'],
            ['prng', '--seed', '1', '--kind', 'weighted', '--weights', '0,0'],
            ['prng', '--seed', '1', '--kind', 'weighted', '--weights', '9223372036854775807,1'],
            ['prng', '--kind', 'words'],
            ['solve'],
            ['exact', '--door', '4'],
            ['exact', '--doors', '1_0'],
            ['exact', '--prior', '-h'],
            ['exact', '--doors', '--help'],
            ['exact', '--prior', '1,2,3,'],
            ['exact', '--mixed', '1/9223372036854775808'],
            ['optimum', '--strategy', 'switch', '--cost', '9223372036854775808'],
            ['simulate', '--se', '1'],
            ['simulate', '--seed', '1', '--trials', '5', '--mixed', '1/18446744073709551615'],
        ];
        $named = [];
        foreach ($cases as $case) {
            $named[implode(' ', $case)] = [$case];
        }
        return $named;
    }

    #[DataProvider('invalidInvocations')]
    public function testInvalidInputExitsWithUsageError(array $arguments): void
    {
        [$code, $stdout, $stderr] = self::invoke($arguments);
        self::assertSame(2, $code);
        self::assertSame('', $stdout);
        self::assertStringStartsWith('error: ', $stderr);
    }

    public function testExactDefaultOutput(): void
    {
        [$code, $stdout] = self::invoke(['exact']);
        self::assertSame(0, $code);
        self::assertSame(
            [
                'command' => 'exact',
                'scenario' => [
                    'doors' => 3, 'prizes' => 1, 'prior' => 'uniform', 'pick' => 0, 'reveals' => 1,
                    'host' => 'informed', 'host_weights' => null, 'mixed' => '1/2', 'observed' => null,
                ],
                'prize_at_pick' => '1/3',
                'outcomes' => ['decision' => '1/1', 'void' => '0/1', 'no_offer' => '0/1', 'observed' => null],
                'win' => ['stay' => '1/3', 'switch' => '2/3', 'mixed' => '1/2'],
            ],
            self::decode($stdout),
        );
    }

    public function testEqualsSyntaxAndNormalizedEcho(): void
    {
        [$code, $stdout] = self::invoke(['exact', '--doors=6', '--reveals=2', '--observed=4,1', '--mixed', '2/4']);
        self::assertSame(0, $code);
        $scenario = self::decode($stdout)['scenario'];
        self::assertIsArray($scenario);
        self::assertSame([1, 4], $scenario['observed']);
        self::assertSame('1/2', $scenario['mixed']);
    }

    public function testEmptyObservationForZeroReveals(): void
    {
        [$code, $stdout] = self::invoke(['exact', '--reveals', '0', '--observed', '']);
        self::assertSame(0, $code);
        $outcomes = self::decode($stdout)['outcomes'];
        self::assertIsArray($outcomes);
        self::assertSame('1/1', $outcomes['observed']);
    }

    public function testSimulateSpecExample(): void
    {
        [$code, $stdout] = self::invoke(['simulate', '--host', 'random', '--seed', '1', '--trials', '1000']);
        self::assertSame(0, $code);
        $report = self::decode($stdout);
        self::assertSame(['decision' => 675, 'void' => 325, 'no_offer' => 0, 'observed' => null], $report['counts']);
        self::assertSame(675, $report['sample_size']);
        $strategies = $report['strategies'];
        self::assertIsArray($strategies);
        $stay = $strategies['stay'];
        self::assertIsArray($stay);
        self::assertSame(343, $stay['wins']);
        self::assertEqualsWithDelta(343 / 675, $stay['rate'], 1e-12);
    }

    public function testSimulateEmptySampleReportsNull(): void
    {
        [$code, $stdout] = self::invoke(['simulate', '--doors', '4', '--prior', '0,0,0,1', '--observed', '3', '--seed', '2', '--trials', '50']);
        self::assertSame(0, $code);
        $report = self::decode($stdout);
        self::assertSame(0, $report['sample_size']);
        self::assertSame(
            ['wins' => 0, 'rate' => null, 'wilson95' => null],
            SpecDataView::at($report, 'strategies', 'switch'),
        );
    }

    public function testRatesAreFloatsEvenWhenWhole(): void
    {
        [, $stdout] = self::invoke(['simulate', '--host', 'adversarial', '--seed', '4', '--trials', '30']);
        self::assertStringContainsString('"rate": 1.0', $stdout);
        self::assertStringContainsString('"rate": 0.0', $stdout);
    }

    public function testOptimumOmitsReveals(): void
    {
        [$code, $stdout] = self::invoke(['optimum', '--doors', '5', '--strategy', 'switch', '--cost', '1/20']);
        self::assertSame(0, $code);
        $report = self::decode($stdout);
        self::assertNull(SpecDataView::at($report, 'scenario', 'reveals'));
        self::assertSame('1/20', $report['cost']);
        self::assertSame(['reveals' => 3, 'value' => '13/20'], $report['optimum']);
    }

    public function testPrngKinds(): void
    {
        self::assertSame(['16294208416658607535'], self::decode(self::invoke(['prng', '--seed', '0', '--kind', 'splitmix'])[1])['values']);
        $bounded = self::decode(self::invoke(['prng', '--seed', '3', '--kind', 'bounded', '--bound', '6', '--count', '5'])[1]);
        self::assertSame(6, $bounded['bound']);
        self::assertCount(5, SpecDataView::list($bounded, 'values'));
        $weighted = self::decode(self::invoke(['prng', '--seed', '3', '--kind', 'weighted', '--weights', '0,1', '--count', '4'])[1]);
        self::assertSame([1, 1, 1, 1], $weighted['values']);
        $shuffle = self::decode(self::invoke(['prng', '--seed', '3', '--kind', 'shuffle', '--size', '6'])[1]);
        $values = SpecDataView::list($shuffle, 'values');
        sort($values);
        self::assertSame([0, 1, 2, 3, 4, 5], $values);
    }

    public function testValuesMayStartWithAMinusSignAndHaveLeadingZeros(): void
    {
        [$code, $stdout] = self::invoke(['exact', '--mixed', '-1/-2', '--doors', ' +04']);
        self::assertSame(0, $code);
        $report = self::decode($stdout);
        self::assertSame('1/2', SpecDataView::at($report, 'scenario', 'mixed'));
        self::assertSame(4, SpecDataView::at($report, 'scenario', 'doors'));
        [$code, $stdout] = self::invoke(['optimum', '--strategy', 'switch', '--cost', '-0/1']);
        self::assertSame(0, $code);
        self::assertSame('0/1', self::decode($stdout)['cost']);
    }

    public function testHelpWinsOverOtherErrors(): void
    {
        [$code, $stdout] = self::invoke(['exact', '--doors', '1_0', '--bogus', '5', '-h']);
        self::assertSame(0, $code);
        self::assertStringContainsString('usage: monty-lab', $stdout);
    }

    public function testHelpAndVersion(): void
    {
        [$code, $stdout] = self::invoke(['--help']);
        self::assertSame(0, $code);
        self::assertStringContainsString('usage: monty-lab', $stdout);
        [$code, $stdout] = self::invoke(['exact', '-h']);
        self::assertSame(0, $code);
        self::assertStringContainsString('usage: monty-lab', $stdout);
        [$code, $stdout] = self::invoke(['--version']);
        self::assertSame(0, $code);
        self::assertSame('monty-lab ' . Cli::VERSION . PHP_EOL, $stdout);
        [$code, , $stderr] = self::invoke([]);
        self::assertSame(2, $code);
        self::assertStringContainsString('usage: monty-lab', $stderr);
    }

    public function testClosedOutputReturnsBrokenPipeCode(): void
    {
        $stdout = fopen('php://memory', 'r');
        $stderr = fopen('php://memory', 'w+');
        if ($stdout === false || $stderr === false) {
            throw new RuntimeException('cannot open memory streams');
        }
        self::assertSame(141, Cli::main(['monty-lab', 'exact'], $stdout, $stderr));
    }

    private static function invoke(array $arguments): array
    {
        $stdout = fopen('php://memory', 'w+');
        $stderr = fopen('php://memory', 'w+');
        if ($stdout === false || $stderr === false) {
            throw new RuntimeException('cannot open memory streams');
        }
        $code = Cli::main(['monty-lab', ...$arguments], $stdout, $stderr);
        rewind($stdout);
        rewind($stderr);
        return [$code, (string) stream_get_contents($stdout), (string) stream_get_contents($stderr)];
    }

    private static function decode(mixed $json): array
    {
        $decoded = json_decode(is_string($json) ? $json : '', true, 512, JSON_THROW_ON_ERROR);
        self::assertIsArray($decoded);
        return $decoded;
    }
}
