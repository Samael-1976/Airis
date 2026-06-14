<?php
// ============================================================================
// AIRIS TRACKER API (Mini-Firebase)
// Motore di sincronizzazione P2P per omnia-diffusion.com
// ============================================================================

// 1. INTESTAZIONI CORS (Permette ad Airis di comunicare dal PC locale)
header("Access-Control-Allow-Origin: *");
header("Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE, OPTIONS");
header("Access-Control-Allow-Headers: Content-Type, X-Airis-Key");
header("Content-Type: application/json");

// Risposta rapida per il preflight CORS
if ($_SERVER['REQUEST_METHOD'] == 'OPTIONS') {
    http_response_code(200);
    exit(0);
}

// 2. CONFIGURAZIONE SICUREZZA
$PUBLIC_NETWORK_KEY = "Airis_Omnia_Network_Key_2026_v1"; // La chiave che metteremo nel Python
$DB_FILE = __DIR__ . '/airis_db.json';
$RATE_LIMIT_FILE = __DIR__ . '/rate_limit.json';
$MAX_REQUESTS_PER_MINUTE = 60; // Limite anti-troll (Bot protection)

// 3. LO SCUDO DI ARUBA (IP Rate Limiting)
$client_ip = $_SERVER['REMOTE_ADDR'];
$method = $_SERVER['REQUEST_METHOD'];

// Applichiamo il rate limit solo alle scritture (PUT, POST, PATCH, DELETE)
if ($method !== 'GET') {
    // Verifica Chiave
    $provided_key = isset($_SERVER['HTTP_X_AIRIS_KEY']) ? $_SERVER['HTTP_X_AIRIS_KEY'] : '';
    if ($provided_key !== $PUBLIC_NETWORK_KEY) {
        http_response_code(401);
        echo json_encode(["error" => "Permission denied. Invalid Network Key."]);
        exit(0);
    }

    // Verifica IP Spam
    $fp_rate = fopen($RATE_LIMIT_FILE, 'c+');
    if (flock($fp_rate, LOCK_EX)) {
        $rate_data = json_decode(file_get_contents($RATE_LIMIT_FILE), true) ?:[];
        $current_time = time();
        
        // Pulisci vecchi log
        foreach ($rate_data as $ip => $requests) {
            $rate_data[$ip] = array_filter($requests, function($timestamp) use ($current_time) {
                return ($current_time - $timestamp) < 60;
            });
            if (empty($rate_data[$ip])) unset($rate_data[$ip]);
        }

        $ip_requests = isset($rate_data[$client_ip]) ? $rate_data[$client_ip] :[];
        
        if (count($ip_requests) >= $MAX_REQUESTS_PER_MINUTE) {
            flock($fp_rate, LOCK_UN);
            fclose($fp_rate);
            http_response_code(429);
            echo json_encode(["error" => "Too Many Requests. Lo Scudo di Aruba ti ha bloccato."]);
            exit(0);
        }

        $rate_data[$client_ip][] = $current_time;
        ftruncate($fp_rate, 0);
        rewind($fp_rate);
        fwrite($fp_rate, json_encode($rate_data));
        flock($fp_rate, LOCK_UN);
    }
    fclose($fp_rate);
}

// 4. PARSING DEL PERCORSO (Stile Firebase)
// Es: ?path=gilde/123/membri/456.json
$path_param = isset($_GET['path']) ? $_GET['path'] : '';
$path_param = str_replace('.json', '', $path_param);
$path_keys = array_filter(explode('/', $path_param), 'strlen');

// 5. LETTURA E SCRITTURA DEL DATABASE (Con File Locking per prevenire corruzione)
$fp_db = fopen($DB_FILE, 'c+');
if (!$fp_db) {
    http_response_code(500);
    echo json_encode(["error" => "Impossibile aprire il database."]);
    exit(0);
}

if (flock($fp_db, $method === 'GET' ? LOCK_SH : LOCK_EX)) {
    $filesize = filesize($DB_FILE);
    $db_content = $filesize > 0 ? fread($fp_db, $filesize) : '{}';
    $db_data = json_decode($db_content, true) ?:[];

    // Navigazione dell'albero JSON
    $current = &$db_data;
    $parent = null;
    $last_key = null;

    foreach ($path_keys as $key) {
        $parent = &$current;
        $last_key = $key;
        if (!isset($current[$key]) || !is_array($current[$key])) {
            if ($method === 'GET') {
                $current = null; // Nodo non trovato
                break;
            }
            $current[$key] = [];
        }
        $current = &$current[$key];
    }

    // ESECUZIONE METODO
    if ($method === 'GET') {
        echo json_encode($current !== null ? $current : new stdClass());
    } 
    else {
        $input_data = json_decode(file_get_contents('php://input'), true);
        if ($input_data === null && json_last_error() !== JSON_ERROR_NONE) {
            // Se non è un JSON valido, prendi la stringa grezza (es. per i nomi)
            $input_data = trim(file_get_contents('php://input'), '"');
        }

        if ($method === 'PUT') {
            if (empty($path_keys)) {
                $db_data = $input_data; // Sovrascrive tutto
            } else {
                $parent[$last_key] = $input_data;
            }
        } 
        elseif ($method === 'PATCH') {
            if (is_array($current) && is_array($input_data)) {
                foreach ($input_data as $k => $v) {
                    $current[$k] = $v;
                }
            } else {
                if (empty($path_keys)) $db_data = $input_data;
                else $parent[$last_key] = $input_data;
            }
        } 
        elseif ($method === 'DELETE') {
            if (!empty($path_keys) && isset($parent[$last_key])) {
                unset($parent[$last_key]);
            } elseif (empty($path_keys)) {
                $db_data =[];
            }
        }

        // Salvataggio
        ftruncate($fp_db, 0);
        rewind($fp_db);
        fwrite($fp_db, json_encode($db_data, JSON_PRETTY_PRINT));
        echo json_encode(["status" => "ok"]);
    }

    flock($fp_db, LOCK_UN);
} else {
    http_response_code(503);
    echo json_encode(["error" => "Database bloccato da un altro processo. Riprova."]);
}
fclose($fp_db);
?>