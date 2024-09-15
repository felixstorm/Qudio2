<?php
    // break on all errors (copied from https://stackoverflow.com/a/10973728)
    set_error_handler(
        function(int $nSeverity, string $strMessage, string $strFilePath, int $nLineNumber){
            if(error_reporting()!==0) // Not error suppression operator @
                throw new ErrorException($strMessage, /*nExceptionCode*/ 0, $nSeverity, $strFilePath, $nLineNumber);
        },
        /*E_ALL*/ -1
    );

    $url = 'http://localhost:3678/token';
    $options = array(
        'http' => array(
            'method'  => 'POST',
        )
    );
    $context  = stream_context_create($options);
    $access_token_result = file_get_contents($url, false, $context);

    header('Content-Type: application/javascript');
?>
var spotifyAccessTokenResult = <?php echo $access_token_result; ?>;
