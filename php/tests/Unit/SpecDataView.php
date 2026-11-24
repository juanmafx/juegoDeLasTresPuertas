<?php

// Typed accessors into decoded JSON reports for the CLI tests.

declare(strict_types=1);

namespace MontyHall\Lab\Tests\Unit;

use RuntimeException;

final class SpecDataView
{
    public static function at(array $data, string ...$path): mixed
    {
        $current = $data;
        foreach ($path as $key) {
            if (!is_array($current) || !array_key_exists($key, $current)) {
                throw new RuntimeException('missing key ' . $key);
            }
            $current = $current[$key];
        }
        return $current;
    }

    public static function list(array $data, string $key): array
    {
        $value = self::at($data, $key);
        if (!is_array($value)) {
            throw new RuntimeException($key . ' is not a list');
        }
        return $value;
    }
}
