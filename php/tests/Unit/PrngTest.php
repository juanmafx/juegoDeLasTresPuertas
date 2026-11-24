<?php

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use InvalidArgumentException;
use MontyHall\Lab\Prng\SplitMix64;
use MontyHall\Lab\Prng\Uint64;
use MontyHall\Lab\Prng\Xoshiro256StarStar;
use MontyHall\Lab\Tests\SpecData;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class PrngTest extends TestCase
{
    public static function vectors(): array
    {
        return SpecData::list('prng-vectors.json', 'vectors');
    }

    #[DataProvider('vectors')]
    public function testGoldenVector(array $vector): void
    {
        $seed = SpecData::int($vector['seed']);
        $rng = new Xoshiro256StarStar($seed);
        $count = isset($vector['count']) ? SpecData::int($vector['count']) : 0;
        $actual = [];
        switch ($vector['kind']) {
            case 'splitmix':
                $expander = new SplitMix64($seed);
                for ($i = 0; $i < $count; $i++) {
                    $actual[] = Uint64::toDecimal($expander->next());
                }
                break;
            case 'words':
                for ($i = 0; $i < $count; $i++) {
                    $actual[] = Uint64::toDecimal($rng->nextU64());
                }
                break;
            case 'bounded':
                for ($i = 0; $i < $count; $i++) {
                    $actual[] = $rng->bounded(SpecData::int($vector['bound']));
                }
                break;
            case 'weighted':
                for ($i = 0; $i < $count; $i++) {
                    $actual[] = $rng->weightedIndex(SpecData::ints($vector['weights']));
                }
                break;
            default:
                $actual = $rng->shuffle(range(0, SpecData::int($vector['size']) - 1));
        }
        self::assertSame($vector['values'], $actual);
    }

    public function testSplitMixFirstOutputForSeedZero(): void
    {
        self::assertSame('16294208416658607535', Uint64::toDecimal((new SplitMix64(0))->next()));
    }

    public function testUnitWeightsMatchBoundedDraws(): void
    {
        $weighted = new Xoshiro256StarStar(42);
        $bounded = new Xoshiro256StarStar(42);
        for ($i = 0; $i < 200; $i++) {
            self::assertSame($bounded->bounded(7), $weighted->weightedIndex(array_fill(0, 7, 1)));
        }
    }

    public function testZeroWeightIsNeverChosen(): void
    {
        $rng = new Xoshiro256StarStar(7);
        for ($i = 0; $i < 500; $i++) {
            self::assertNotSame(1, $rng->weightedIndex([3, 0, 5]));
        }
    }

    public function testEmptySampleConsumesNothing(): void
    {
        $sampled = new Xoshiro256StarStar(9);
        $fresh = new Xoshiro256StarStar(9);
        self::assertSame([], $sampled->weightedSample([1, 2, 3], [1, 1, 1], 0));
        self::assertSame($fresh->nextU64(), $sampled->nextU64());
    }

    public function testSampleIsDistinctAndFromItems(): void
    {
        $rng = new Xoshiro256StarStar(11);
        $sample = $rng->weightedSample([10, 20, 30, 40, 50], [1, 2, 3, 4, 5], 5);
        sort($sample);
        self::assertSame([10, 20, 30, 40, 50], $sample);
    }

    public function testInvalidInputsAreRejected(): void
    {
        $rng = new Xoshiro256StarStar(1);
        $this->expectException(InvalidArgumentException::class);
        $rng->bounded(0);
    }

    public function testNegativeWeightIsRejected(): void
    {
        $this->expectException(InvalidArgumentException::class);
        (new Xoshiro256StarStar(1))->weightedIndex([1, -1]);
    }

    public function testZeroTotalIsRejected(): void
    {
        $this->expectException(InvalidArgumentException::class);
        (new Xoshiro256StarStar(1))->weightedIndex([0, 0]);
    }
}
