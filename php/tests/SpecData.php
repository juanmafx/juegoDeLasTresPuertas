<?php

// Loads the shared JSON files under spec/ for the test suite.

declare(strict_types=1);

namespace MontyHall\Lab\Tests;

use MontyHall\Lab\Fraction;
use MontyHall\Lab\Host;
use MontyHall\Lab\Scenario;
use RuntimeException;

final class SpecData
{
    public static function load(string $file): array
    {
        $path = dirname(__DIR__, 2) . '/spec/' . $file;
        $text = file_get_contents($path);
        if ($text === false) {
            throw new RuntimeException('cannot read ' . $path);
        }
        $data = json_decode($text, true, 512, JSON_THROW_ON_ERROR);
        if (!is_array($data)) {
            throw new RuntimeException('unexpected JSON in ' . $path);
        }
        return $data;
    }

    public static function list(string $file, string $key): array
    {
        $entries = self::load($file)[$key] ?? null;
        if (!is_array($entries)) {
            throw new RuntimeException('missing ' . $key . ' in ' . $file);
        }
        $cases = [];
        foreach ($entries as $entry) {
            if (!is_array($entry) || !is_string($entry['id'] ?? null)) {
                throw new RuntimeException('malformed entry in ' . $file);
            }
            $cases[$entry['id']] = [$entry];
        }
        return $cases;
    }

    public static function scenario(array $data): Scenario
    {
        return new Scenario(
            doors: self::int($data['doors']),
            prizes: self::int($data['prizes']),
            prior: $data['prior'] === 'uniform' ? null : self::ints($data['prior']),
            pick: self::int($data['pick']),
            reveals: self::int($data['reveals']),
            host: Host::from(self::string($data['host'])),
            hostWeights: $data['host_weights'] === null ? null : self::ints($data['host_weights']),
            mixed: Fraction::parse(self::string($data['mixed'])),
            observed: $data['observed'] === null ? null : self::ints($data['observed']),
        );
    }

    public static function int(mixed $value): int
    {
        if (!is_int($value)) {
            throw new RuntimeException('expected an integer');
        }
        return $value;
    }

    public static function string(mixed $value): string
    {
        if (!is_string($value)) {
            throw new RuntimeException('expected a string');
        }
        return $value;
    }

    public static function array(mixed $value): array
    {
        if (!is_array($value)) {
            throw new RuntimeException('expected an array');
        }
        return $value;
    }

    public static function ints(mixed $value): array
    {
        return array_map(self::int(...), array_values(self::array($value)));
    }
}
