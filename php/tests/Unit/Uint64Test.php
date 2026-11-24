<?php

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use Brick\Math\BigInteger;
use MontyHall\Lab\Prng\Uint64;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class Uint64Test extends TestCase
{
    public static function pairs(): array
    {
        $values = [
            '0', '1', '2', '5', '9', '4294967295', '4294967296', '9223372036854775807',
            '9223372036854775808', '11400714819323198485', '13787848793156543929', '18446744073709551615',
            '16294208416658607535', '123456789012345678', '18446744069414584321',
        ];
        $cases = [];
        foreach ($values as $a) {
            foreach ($values as $b) {
                $cases[$a . '*' . $b] = [$a, $b];
            }
        }
        return $cases;
    }

    #[DataProvider('pairs')]
    public function testArithmeticMatchesArbitraryPrecision(string $a, string $b): void
    {
        $modulus = BigInteger::of(2)->power(64);
        $x = self::native($a);
        $y = self::native($b);
        $product = BigInteger::of($a)->multipliedBy($b);
        self::assertSame($product->mod($modulus)->toString(), Uint64::toDecimal(Uint64::multiply($x, $y)));
        [$high, $low] = Uint64::multiplyFull($x, $y);
        self::assertSame($product->quotient($modulus)->toString(), Uint64::toDecimal($high));
        self::assertSame($product->mod($modulus)->toString(), Uint64::toDecimal($low));
        self::assertSame(BigInteger::of($a)->plus($b)->mod($modulus)->toString(), Uint64::toDecimal(Uint64::add($x, $y)));
        self::assertSame(BigInteger::of($a)->compareTo($b) < 0, Uint64::lessThan($x, $y));
    }

    public function testShiftsAndRotations(): void
    {
        self::assertSame(1, Uint64::shiftRight(-1, 63));
        self::assertSame(PHP_INT_MAX, Uint64::shiftRight(-1, 1));
        self::assertSame(-1, Uint64::shiftRight(-1, 0));
        self::assertSame(PHP_INT_MIN, Uint64::rotateLeft(1, 63));
        self::assertSame(1, Uint64::rotateLeft(PHP_INT_MIN, 1));
        self::assertSame(Uint64::fromHalves(0x00000001, 0x80000000), Uint64::rotateLeft(Uint64::fromHalves(0, 0xC0000000), 1));
    }

    public function testTwoPow64Mod(): void
    {
        $modulus = BigInteger::of(2)->power(64);
        foreach ([1, 2, 3, 7, 10, 1_000_000, 4294967296, 6148914691236517205, PHP_INT_MAX] as $n) {
            self::assertSame($modulus->mod($n)->toInt(), Uint64::twoPow64Mod($n), (string) $n);
        }
    }

    private static function native(string $decimal): int
    {
        $value = BigInteger::of($decimal);
        if ($value->isGreaterThan(PHP_INT_MAX)) {
            $value = $value->minus(BigInteger::of(2)->power(64));
        }
        return $value->toInt();
    }
}
