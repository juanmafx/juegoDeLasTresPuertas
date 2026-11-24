<?php

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use MontyHall\Lab\Fraction;
use MontyHall\Lab\ScenarioError;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class FractionTest extends TestCase
{
    public function testReducesAndNormalizesSign(): void
    {
        self::assertSame('1/2', Fraction::of(2, 4)->toString());
        self::assertSame('-3/20', Fraction::of(3, -20)->toString());
        self::assertSame('0/1', Fraction::of(0, -7)->toString());
        self::assertSame('5/1', Fraction::of(5)->toString());
    }

    public function testArithmetic(): void
    {
        $third = Fraction::of(1, 3);
        $half = Fraction::of(1, 2);
        self::assertSame('5/6', $third->plus($half)->toString());
        self::assertSame('-1/6', $third->minus($half)->toString());
        self::assertSame('1/6', $third->times($half)->toString());
        self::assertSame('2/3', $third->dividedBy($half)->toString());
        self::assertSame(-1, $third->compareTo($half));
        self::assertSame(0, Fraction::of(2, 6)->compareTo($third));
        self::assertTrue(Fraction::of(2, 6)->equals($third));
    }

    public function testExceedsSixtyFourBits(): void
    {
        $big = Fraction::of(1, PHP_INT_MAX)->times(Fraction::of(1, PHP_INT_MAX));
        self::assertSame('1/85070591730234615847396907784232501249', $big->toString());
    }

    public function testFloor(): void
    {
        self::assertSame('2', Fraction::of(5, 2)->floor()->toString());
        self::assertSame('-3', Fraction::of(-5, 2)->floor()->toString());
        self::assertSame('-2', Fraction::of(-4, 2)->floor()->toString());
        self::assertSame('0', Fraction::of(1, 3)->floor()->toString());
    }

    public static function validTexts(): array
    {
        return [
            ['1/2', '1/2'], ['3', '3/1'], [' 4/8 ', '1/2'], ['-6/4', '-3/2'], ['+1/3', '1/3'], ['0', '0/1'],
            ['-1/-2', '1/2'], ['-0/5', '0/1'], ["\f04/\t8", '1/2'],
            ['9223372036854775807/9223372036854775807', '1/1'], ['-9223372036854775807', '-9223372036854775807/1'],
        ];
    }

    #[DataProvider('validTexts')]
    public function testParse(string $text, string $expected): void
    {
        self::assertSame($expected, Fraction::parse($text)->toString());
    }

    public static function invalidTexts(): array
    {
        return [
            ['1/0'], ['a'], [''], ['1/2/3'], ['1.5'], ['/2'], ['2/'], ['1_0/2'], ["\u{FF11}/2"], ["1/\u{A0}2"],
            ["1\0"], ['1/9223372036854775808'], ['-9223372036854775808'], ['1/1' . str_repeat('0', 5000)],
        ];
    }

    #[DataProvider('invalidTexts')]
    public function testParseRejects(string $text): void
    {
        $this->expectException(ScenarioError::class);
        Fraction::parse($text);
    }

    public function testDivisionByZero(): void
    {
        $this->expectException(ScenarioError::class);
        Fraction::one()->dividedBy(Fraction::zero());
    }
}
