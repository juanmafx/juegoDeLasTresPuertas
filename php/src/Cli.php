<?php

// Command-line contract shared by every language implementation, defined in spec/cli.md.

declare(strict_types=1);

namespace MontyHall\Lab;

use Throwable;
use MontyHall\Lab\Prng\SplitMix64;
use MontyHall\Lab\Prng\Uint64;
use MontyHall\Lab\Prng\Xoshiro256StarStar;

final class Cli
{
    public const string VERSION = '3.0.0';
    public const int EXIT_OK = 0;
    public const int EXIT_USAGE = 2;
    public const int EXIT_BROKEN_PIPE = 141;
    public const int MAX_PRNG_COUNT = 100_000;
    public const int MAX_SHUFFLE_SIZE = 10_000;

    private const array SCENARIO_FLAGS = ['doors', 'prizes', 'prior', 'pick', 'host', 'host-weights', 'mixed'];
    private const array FLAGS = [
        'exact' => [...self::SCENARIO_FLAGS, 'reveals', 'observed'],
        'simulate' => [...self::SCENARIO_FLAGS, 'reveals', 'observed', 'trials', 'seed'],
        'optimum' => [...self::SCENARIO_FLAGS, 'strategy', 'cost'],
        'prng' => ['seed', 'kind', 'count', 'bound', 'weights', 'size'],
    ];
    private const string USAGE = <<<'TEXT'
        usage: monty-lab {exact,simulate,optimum,prng} [flags]

        Generalized Monty Hall decision lab (cross-language contract, see spec/cli.md).

          exact     exact win probabilities as fractions
          simulate  deterministic Monte Carlo simulation (--seed required)
          optimum   value of exploration over all reveal counts (--strategy required)
          prng      raw generator output for conformance vectors (--seed and --kind required)

        TEXT;

    public static function main(array $argv, mixed $stdout = STDOUT, mixed $stderr = STDERR): int
    {
        if (!is_resource($stdout) || !is_resource($stderr)) {
            return 1;
        }
        $arguments = array_values(array_map(strval(...), array_slice($argv, 1)));
        if ($arguments === [] || in_array('-h', $arguments, true) || in_array('--help', $arguments, true)) {
            fwrite($arguments === [] ? $stderr : $stdout, self::USAGE);
            return $arguments === [] ? self::EXIT_USAGE : self::EXIT_OK;
        }
        if ($arguments[0] === '--version') {
            fwrite($stdout, 'monty-lab ' . self::VERSION . PHP_EOL);
            return self::EXIT_OK;
        }
        try {
            $report = self::run($arguments);
            $encoded = json_encode(
                $report,
                JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_PRESERVE_ZERO_FRACTION | JSON_THROW_ON_ERROR,
            ) . PHP_EOL;
        } catch (ScenarioError $error) {
            fwrite($stderr, 'error: ' . $error->getMessage() . PHP_EOL);
            return self::EXIT_USAGE;
        } catch (Throwable $error) {
            fwrite($stderr, 'error: internal failure: ' . $error->getMessage() . PHP_EOL);
            return 1;
        }
        $written = @fwrite($stdout, $encoded);
        if ($written === false || $written < strlen($encoded) || !@fflush($stdout)) {
            return self::EXIT_BROKEN_PIPE;
        }
        return self::EXIT_OK;
    }

    public static function run(array $arguments): array
    {
        $command = array_shift($arguments);
        if (!is_string($command) || !array_key_exists($command, self::FLAGS)) {
            throw new ScenarioError(sprintf('invalid command %s (choose from exact, simulate, optimum, prng)', json_encode($command)));
        }
        $flags = self::parseFlags($command, $arguments);
        return match ($command) {
            'exact' => self::exactReport(self::scenarioFromFlags($flags, true)),
            'simulate' => self::simulateReport(
                self::scenarioFromFlags($flags, true),
                self::integer('trials', $flags['trials'] ?? '100000'),
                self::integer('seed', self::required($flags, 'seed')),
            ),
            'optimum' => self::optimumReport(
                self::scenarioFromFlags($flags, false),
                self::strategy(self::required($flags, 'strategy')),
                Fraction::parse($flags['cost'] ?? '0'),
            ),
            default => self::prngReport($flags),
        };
    }

    public static function exactReport(Scenario $scenario): array
    {
        $result = Solver::solve($scenario);
        return [
            'command' => 'exact',
            'scenario' => $scenario->toJson(),
            'prize_at_pick' => $result->prizeAtPick->toString(),
            'outcomes' => [
                'decision' => $result->decision->toString(),
                'void' => $result->void->toString(),
                'no_offer' => $result->noOffer->toString(),
                'observed' => $result->observed?->toString(),
            ],
            'win' => [
                'stay' => $result->stay?->toString(),
                'switch' => $result->switch?->toString(),
                'mixed' => $result->mixed($scenario->mixed)?->toString(),
            ],
        ];
    }

    public static function simulateReport(Scenario $scenario, int $trials, int $seed): array
    {
        $counts = Simulator::simulate($scenario, $trials, $seed);
        $sample = $counts->sampleSize();
        return [
            'command' => 'simulate',
            'scenario' => $scenario->toJson(),
            'seed' => $seed,
            'trials' => $trials,
            'counts' => [
                'decision' => $counts->decision,
                'void' => $counts->void,
                'no_offer' => $counts->noOffer,
                'observed' => $counts->observed,
            ],
            'sample_size' => $sample,
            'strategies' => [
                'stay' => self::strategySummary($counts->stayWins, $sample),
                'switch' => self::strategySummary($counts->switchWins, $sample),
                'mixed' => self::strategySummary($counts->mixedWins, $sample),
            ],
        ];
    }

    public static function optimumReport(Scenario $scenario, Strategy $strategy, Fraction $cost): array
    {
        $result = Optimum::curve($scenario, $strategy, $cost);
        $echoed = $scenario->toJson();
        $echoed['reveals'] = null;
        $parabola = null;
        $fit = $result->parabola;
        if ($fit !== null) {
            $parabola = [
                'a' => $fit->a->toString(),
                'b' => $fit->b->toString(),
                'c' => $fit->c->toString(),
                'shape' => $fit->shape(),
                'residual_sum_of_squares' => $fit->residualSumOfSquares->toString(),
                'vertex' => null,
                'vertex_offset' => null,
                'vertex_value_gap' => null,
                'rounded_vertex' => null,
                'fitted_choice' => self::choice($result, $fit->fittedChoice),
            ];
            if ($fit->vertexReveals !== null && $fit->vertexValue !== null) {
                $parabola['vertex'] = [
                    'reveals' => $fit->vertexReveals->toString(),
                    'value' => $fit->vertexValue->toString(),
                ];
                $parabola['vertex_offset'] = $fit->vertexReveals->minus(Fraction::of($result->best->reveals))->toString();
                $parabola['vertex_value_gap'] = $fit->vertexValue->minus($result->best->value)->toString();
            }
            if ($fit->roundedVertex !== null) {
                $parabola['rounded_vertex'] = self::choice($result, $fit->roundedVertex);
            }
        }
        $curve = [];
        foreach ($result->curve as $point) {
            assert($point instanceof CurvePoint);
            $curve[] = ['reveals' => $point->reveals, 'win' => $point->win->toString(), 'value' => $point->value->toString()];
        }
        return [
            'command' => 'optimum',
            'scenario' => $echoed,
            'strategy' => $strategy->value,
            'cost' => $cost->toString(),
            'curve' => $curve,
            'optimum' => ['reveals' => $result->best->reveals, 'value' => $result->best->value->toString()],
            'parabola' => $parabola,
        ];
    }

    public static function prngReport(array $flags): array
    {
        $seed = self::integer('seed', self::required($flags, 'seed'));
        $kind = self::required($flags, 'kind');
        $count = self::integer('count', $flags['count'] ?? '1');
        if ($seed < 0) {
            throw new ScenarioError(sprintf('seed must be between 0 and %d', Scenario::MAX_SEED));
        }
        if ($count < 1 || $count > self::MAX_PRNG_COUNT) {
            throw new ScenarioError(sprintf('count must be between 1 and %d', self::MAX_PRNG_COUNT));
        }
        $rng = new Xoshiro256StarStar($seed);
        $report = ['command' => 'prng', 'seed' => $seed, 'kind' => $kind];
        $values = [];
        switch ($kind) {
            case 'splitmix':
                $expander = new SplitMix64($seed);
                for ($i = 0; $i < $count; $i++) {
                    $values[] = Uint64::toDecimal($expander->next());
                }
                break;
            case 'words':
                for ($i = 0; $i < $count; $i++) {
                    $values[] = Uint64::toDecimal($rng->nextU64());
                }
                break;
            case 'bounded':
                $bound = isset($flags['bound']) ? self::integer('bound', $flags['bound']) : 0;
                if ($bound < 1) {
                    throw new ScenarioError(sprintf('bound must be between 1 and %d', Scenario::MAX_SEED));
                }
                $report['bound'] = $bound;
                for ($i = 0; $i < $count; $i++) {
                    $values[] = $rng->bounded($bound);
                }
                break;
            case 'weighted':
                $weights = self::integerList('weights', $flags['weights'] ?? '');
                $total = 0;
                foreach ($weights as $weight) {
                    if ($weight < 0) {
                        throw new ScenarioError('weights must be non-negative integers with a positive total');
                    }
                    if ($weight > PHP_INT_MAX - $total) {
                        throw new ScenarioError(sprintf('weights must sum to at most %d', Scenario::MAX_SEED));
                    }
                    $total += $weight;
                }
                if ($total <= 0) {
                    throw new ScenarioError('weights must be non-negative integers with a positive total');
                }
                $report['weights'] = $weights;
                for ($i = 0; $i < $count; $i++) {
                    $values[] = $rng->weightedIndex($weights);
                }
                break;
            case 'shuffle':
                $size = isset($flags['size']) ? self::integer('size', $flags['size']) : 0;
                if ($size < 1 || $size > self::MAX_SHUFFLE_SIZE) {
                    throw new ScenarioError(sprintf('size must be between 1 and %d', self::MAX_SHUFFLE_SIZE));
                }
                $report['size'] = $size;
                $values = $rng->shuffle(range(0, $size - 1));
                break;
            default:
                throw new ScenarioError('kind must be splitmix, words, bounded, weighted or shuffle');
        }
        $report['values'] = $values;
        return $report;
    }

    public static function parseFlags(string $command, array $arguments): array
    {
        $allowed = self::FLAGS[$command];
        $flags = [];
        $count = count($arguments);
        for ($index = 0; $index < $count; $index++) {
            $token = strval($arguments[$index]);
            if (!str_starts_with($token, '--')) {
                throw new ScenarioError(sprintf('unrecognized argument %s', json_encode($token)));
            }
            $name = substr($token, 2);
            $value = null;
            $equals = strpos($name, '=');
            if ($equals !== false) {
                $value = substr($name, $equals + 1);
                $name = substr($name, 0, $equals);
            }
            if (!in_array($name, $allowed, true)) {
                throw new ScenarioError(sprintf('unrecognized argument --%s for %s', $name, $command));
            }
            if ($value === null) {
                if ($index + 1 >= $count) {
                    throw new ScenarioError(sprintf('argument --%s expects one value', $name));
                }
                $value = strval($arguments[++$index]);
            }
            $flags[$name] = $value;
        }
        return $flags;
    }

    public static function scenarioFromFlags(array $flags, bool $withReveals): Scenario
    {
        $prior = $flags['prior'] ?? 'uniform';
        $hostWeights = $flags['host-weights'] ?? null;
        $observed = $flags['observed'] ?? null;
        $host = Host::tryFrom($flags['host'] ?? 'informed');
        if ($host === null) {
            throw new ScenarioError('host must be informed, random, biased or adversarial');
        }
        return new Scenario(
            doors: self::integer('doors', $flags['doors'] ?? '3'),
            prizes: self::integer('prizes', $flags['prizes'] ?? '1'),
            prior: $prior === 'uniform' ? null : self::integerList('prior', $prior),
            pick: self::integer('pick', $flags['pick'] ?? '0'),
            reveals: $withReveals ? self::integer('reveals', $flags['reveals'] ?? '1') : 0,
            host: $host,
            hostWeights: $hostWeights === null ? null : self::integerList('host weights', $hostWeights),
            mixed: Fraction::parse($flags['mixed'] ?? '1/2'),
            observed: $observed === null ? null : self::integerList('observed', $observed),
        );
    }

    public static function integer(string $name, string $text): int
    {
        $trimmed = trim($text);
        if (preg_match('/^[+-]?[0-9]+$/', $trimmed) !== 1) {
            throw new ScenarioError(sprintf('%s must be an integer, got %s', $name, json_encode($text)));
        }
        $value = filter_var($trimmed, FILTER_VALIDATE_INT);
        if ($value === false) {
            throw new ScenarioError(sprintf('%s is out of range: %s', $name, $trimmed));
        }
        return $value;
    }

    public static function integerList(string $name, string $text): array
    {
        if (trim($text) === '') {
            return [];
        }
        return array_map(static fn (string $part): int => self::integer($name, $part), explode(',', $text));
    }

    private static function strategySummary(int $wins, int $sample): array
    {
        if ($sample === 0) {
            return ['wins' => $wins, 'rate' => null, 'wilson95' => null];
        }
        return ['wins' => $wins, 'rate' => (float) $wins / $sample, 'wilson95' => Wilson::interval($wins, $sample)];
    }

    private static function choice(OptimumResult $result, int $reveals): array
    {
        $value = $result->point($reveals)->value;
        return [
            'reveals' => $reveals,
            'value' => $value->toString(),
            'regret' => $result->best->value->minus($value)->toString(),
        ];
    }

    private static function strategy(string $text): Strategy
    {
        return Strategy::tryFrom($text) ?? throw new ScenarioError('strategy must be stay, switch or mixed');
    }

    private static function required(array $flags, string $name): string
    {
        if (!isset($flags[$name])) {
            throw new ScenarioError(sprintf('the following argument is required: --%s', $name));
        }
        return strval($flags[$name]);
    }
}
