<?php
// Per-request code coverage of /var/www/src for the T1-32 pilot. Active only while /tmp/cov/ON exists.
// Writes one line per request to /tmp/cov/index.jsonl and the executed lines (deduplicated by hash) to /tmp/cov/sigs/.
if (PHP_SAPI !== 'cli' && function_exists('xdebug_start_code_coverage') && is_file('/tmp/cov/ON')) {
    xdebug_set_filter(XDEBUG_FILTER_CODE_COVERAGE, XDEBUG_PATH_INCLUDE, ['/var/www/src/']);
    xdebug_start_code_coverage(0);
    $GLOBALS['__cov_t0'] = microtime(true);
    register_shutdown_function(static function () {
        $cov = xdebug_get_code_coverage();
        xdebug_stop_code_coverage(true);
        $files = [];
        foreach ($cov as $file => $lines) {
            $nums = array_keys($lines);
            sort($nums);
            $ranges = [];
            $start = $prev = null;
            foreach ($nums as $n) {
                if ($start === null) { $start = $prev = $n; continue; }
                if ($n === $prev + 1) { $prev = $n; continue; }
                $ranges[] = $start === $prev ? (string)$start : "$start-$prev";
                $start = $prev = $n;
            }
            if ($start !== null) { $ranges[] = $start === $prev ? (string)$start : "$start-$prev"; }
            $files[substr($file, strlen('/var/www/'))] = implode(',', $ranges);
        }
        ksort($files);
        $json = json_encode($files);
        $sig = sha1($json);
        @mkdir('/tmp/cov/sigs', 0777, true);
        $path = "/tmp/cov/sigs/$sig.json.gz";
        if (!is_file($path)) { file_put_contents($path, gzencode($json, 6)); }
        $uri = $_SERVER['REQUEST_URI'] ?? '';
        $q = strpos($uri, '?');
        file_put_contents('/tmp/cov/index.jsonl', json_encode([
            'ts' => $_SERVER['REQUEST_TIME_FLOAT'] ?? null,
            'ms' => (int)round((microtime(true) - $GLOBALS['__cov_t0']) * 1000),
            'm' => $_SERVER['REQUEST_METHOD'] ?? '',
            'u' => $q === false ? $uri : substr($uri, 0, $q),
            'c' => http_response_code(),
            's' => $sig,
            'f' => count($files),
        ]) . "\n", FILE_APPEND | LOCK_EX);
    });
}
