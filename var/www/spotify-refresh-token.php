<?php
    // break on all errors (copied from https://stackoverflow.com/a/10973728)
    set_error_handler(
        function(int $nSeverity, string $strMessage, string $strFilePath, int $nLineNumber){
            if(error_reporting()!==0) // Not error suppression operator @
                throw new ErrorException($strMessage, /*nExceptionCode*/ 0, $nSeverity, $strFilePath, $nLineNumber);
        },
        /*E_ALL*/ -1
    );

    $qudio_ini = parse_ini_file('/mnt/dietpi_userdata/qudio/qudio.ini');

    $url = 'https://accounts.spotify.com/api/token';
    $username = $qudio_ini['SPOTIFY_CLIENT_ID'];
    $password = $qudio_ini['SPOTIFY_CLIENT_SECRET'];
    $post_data = array(
        'grant_type' => 'refresh_token', 
        'refresh_token' => $qudio_ini['SPOTIFY_USER_REFRESH'],
    );

    $options = array(
        'http' => array(
            'header'  => array(
                "Authorization: Basic " . base64_encode("$username:$password"),
                "Content-type: application/x-www-form-urlencoded",
            ),
            'method'  => 'POST',
            'content' => http_build_query($post_data),
        )
    );
    $context  = stream_context_create($options);
    $refresh_token_result = file_get_contents($url, false, $context);

    header('Content-Type: application/javascript');
?>
var spotifyRefreshTokenResult = <?php echo $refresh_token_result; ?>;
