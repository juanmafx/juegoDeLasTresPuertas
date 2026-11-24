<?php

// Unsigned 64-bit arithmetic on PHP's signed integers, using 32-bit and 16-bit limbs so nothing overflows to float.

declare(strict_types=1);

namespace MontyHall\Lab\Prng;

final class Uint64
{
    public const int MASK32 = 0xFFFFFFFF;

    public static function fromHalves(int $high, int $low): int
    {
        return (($high & self::MASK32) << 32) | ($low & self::MASK32);
    }

    public static function shiftRight(int $value, int $bits): int
    {
        if ($bits === 0) {
            return $value;
        }
        return ($value >> $bits) & (PHP_INT_MAX >> ($bits - 1));
    }

    public static function rotateLeft(int $value, int $bits): int
    {
        return ($value << $bits) | self::shiftRight($value, 64 - $bits);
    }

    public static function add(int $a, int $b): int
    {
        $low = ($a & self::MASK32) + ($b & self::MASK32);
        $high = (($a >> 32) & self::MASK32) + (($b >> 32) & self::MASK32) + ($low >> 32);
        return (($high & self::MASK32) << 32) | ($low & self::MASK32);
    }

    public static function multiply(int $a, int $b): int
    {
        $aLow = $a & self::MASK32;
        $aHigh = ($a >> 32) & self::MASK32;
        $bLow = $b & self::MASK32;
        $bHigh = ($b >> 32) & self::MASK32;
        [$carry, $low] = self::multiply32($aLow, $bLow);
        $cross = (self::multiply32($aLow, $bHigh)[1] + self::multiply32($aHigh, $bLow)[1] + $carry) & self::MASK32;
        return ($cross << 32) | $low;
    }

    public static function multiplyFull(int $a, int $b): array
    {
        $aLow = $a & self::MASK32;
        $aHigh = ($a >> 32) & self::MASK32;
        $bLow = $b & self::MASK32;
        $bHigh = ($b >> 32) & self::MASK32;
        [$llHigh, $llLow] = self::multiply32($aLow, $bLow);
        [$lhHigh, $lhLow] = self::multiply32($aLow, $bHigh);
        [$hlHigh, $hlLow] = self::multiply32($aHigh, $bLow);
        [$hhHigh, $hhLow] = self::multiply32($aHigh, $bHigh);
        $column1 = $llHigh + $lhLow + $hlLow;
        $column2 = $lhHigh + $hlHigh + $hhLow + ($column1 >> 32);
        $column3 = $hhHigh + ($column2 >> 32);
        return [
            (($column3 & self::MASK32) << 32) | ($column2 & self::MASK32),
            (($column1 & self::MASK32) << 32) | $llLow,
        ];
    }

    public static function lessThan(int $a, int $b): bool
    {
        return ($a ^ PHP_INT_MIN) < ($b ^ PHP_INT_MIN);
    }

    public static function twoPow64Mod(int $modulus): int
    {
        $half = (PHP_INT_MAX % $modulus + 1) % $modulus;
        return $half >= $modulus - $half ? $half - ($modulus - $half) : $half + $half;
    }

    public static function toDecimal(int $value): string
    {
        return sprintf('%u', $value);
    }

    private static function multiply32(int $a, int $b): array
    {
        $low = $a * ($b & 0xFFFF);
        $high = $a * ($b >> 16);
        $sum = $low + (($high & 0xFFFF) << 16);
        return [($high >> 16) + ($sum >> 32), $sum & self::MASK32];
    }
}
