--TEST--
GHSA-5j3f-64r7-f564 - CGI PATH_INFO pointer bounds (PHP 5.4 compatible)
--SKIPIF--
<?php include "skipif.inc"; ?>
--FILE--
<?php
include "include.inc";
$php = get_cgi_path();
$script = dirname(__FILE__) . '/cgi-path-info-target.php';
file_put_contents($script, '<?php var_dump(isset($_SERVER["PATH_INFO"]) ? $_SERVER["PATH_INFO"] : NULL);');
function run_case($php, $script, $suffix, $pathInfo) {
    $env = array('SCRIPT_FILENAME' => $script . $suffix,
        'PATH_INFO' => $pathInfo,
        'REQUEST_METHOD' => 'GET', 'REDIRECT_STATUS' => '1',
        'PATH' => getenv('PATH'));
    $descriptor = array(0 => array('pipe', 'r'), 1 => array('pipe', 'w'), 2 => array('pipe', 'w'));
    $proc = proc_open(escapeshellarg($php) . ' -n -d cgi.fix_pathinfo=1', $descriptor, $pipes, NULL, $env);
    fclose($pipes[0]);
    $stdout = stream_get_contents($pipes[1]); fclose($pipes[1]);
    $stderr = stream_get_contents($pipes[2]); fclose($pipes[2]);
    $status = proc_close($proc);
    if ($status != 0 || strpos($stdout, 'Content-type:') === FALSE && strpos($stdout, 'Content-Type:') === FALSE) {
        echo "CGI FAILED: " . $status . " " . $stderr . "\n";
        return;
    }
    $parts = preg_split('/\r?\n\r?\n/', $stdout, 2);
    echo isset($parts[1]) ? trim($parts[1]) . "\n" : "NO BODY\n";
}
run_case($php, $script, '/b', '/a/b');
run_case($php, $script, '/xxxxxxxxxxxxxxxx', '/x');
run_case($php, $script, '/xxxxxxxxxxxxxxxx', '');
unlink($script);
?>
--EXPECT--
string(2) "/b"
string(2) "/x"
NULL
