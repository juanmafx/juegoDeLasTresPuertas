<?php

// Summarizes a PHPUnit JUnit log as reports/tests/test-report.md; run after phpunit --log-junit.

declare(strict_types=1);

require dirname(__DIR__) . '/vendor/autoload.php';

$directory = dirname(__DIR__) . '/reports/tests';
$xml = simplexml_load_file($directory . '/junit.xml');
if ($xml === false || !isset($xml->testsuite)) {
    fwrite(STDERR, "error: cannot read junit.xml\n");
    exit(1);
}
$suite = $xml->testsuite;
$tests = (int) $suite['tests'];
$failures = (int) $suite['failures'];
$errors = (int) $suite['errors'];
$skipped = (int) $suite['skipped'];
$assertions = (int) $suite['assertions'];
$passed = $tests - $failures - $errors - $skipped;
$lines = [
    '# Test Report',
    '',
    '- Generated (UTC): ' . gmdate('Y-m-d\TH:i:s\Z'),
    '- PHP: ' . PHP_VERSION . ' (' . PHP_OS_FAMILY . ')',
    '- PHPUnit: ' . PHPUnit\Runner\Version::id(),
    '- Command: `vendor/bin/phpunit --log-junit reports/tests/junit.xml`, then `php tools/write-test-report.php`',
    '- Suite time (s): ' . (string) $suite['time'],
    '',
    '| Total | Passed | Failed | Errors | Skipped | Assertions |',
    '| ---: | ---: | ---: | ---: | ---: | ---: |',
    sprintf('| %d | %d | %d | %d | %d | %d |', $tests, $passed, $failures, $errors, $skipped, $assertions),
    '',
    '| Test class | Tests | Failures | Errors |',
    '| --- | ---: | ---: | ---: |',
];
foreach ($suite->testsuite as $child) {
    foreach ($child->testsuite as $class) {
        $lines[] = sprintf('| %s | %d | %d | %d |', (string) $class['name'], (int) $class['tests'], (int) $class['failures'], (int) $class['errors']);
    }
}
$lines[] = '';
$lines[] = 'Per-test results are in `junit.xml` in this directory.';
file_put_contents($directory . '/test-report.md', implode("\n", $lines) . "\n");
exit($failures + $errors > 0 ? 1 : 0);
