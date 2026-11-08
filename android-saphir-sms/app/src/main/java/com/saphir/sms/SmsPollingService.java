package com.saphir.sms;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.os.PowerManager;
import android.telephony.SmsManager;
import android.util.Log;

import android.Manifest;
import android.content.pm.PackageManager;
import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;

import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okhttp3.WebSocket;
import okhttp3.WebSocketListener;

import org.json.JSONArray;
import org.json.JSONObject;

import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;

public class SmsPollingService extends Service {
    private static final String CHANNEL_ID = "SaphirSmsChannel";
    private static final int NOTIF_ID = 101;
    private static final long HEARTBEAT_INTERVAL_MS = 25000; // 25s Phoenix heartbeat
    private static final long RECONNECT_DELAY_MS = 10000; // 10s auto-reconnect
    private static final long SAFETY_POLL_INTERVAL_MS = 30000; // 30s safety net fallback
    private static final String TOPIC_REALTIME = "realtime:saphir_sms";

    public static final List<String> RECENT_LOGS = Collections.synchronizedList(new ArrayList<>());
    private static final int MAX_LOGS = 60;

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newFixedThreadPool(2);
    private PowerManager.WakeLock wakeLock;

    // Support Pub/Sub en direct via Supabase Realtime WebSocket
    private OkHttpClient wsHttpClient;
    private WebSocket realtimeWebSocket;
    private final AtomicBoolean isWsConnected = new AtomicBoolean(false);
    private Runnable heartbeatRunnable;
    private Runnable reconnectRunnable;
    private Runnable safetyPollRunnable;

    private synchronized OkHttpClient getOkHttpClient() {
        if (wsHttpClient == null) {
            wsHttpClient = new OkHttpClient.Builder()
                    .readTimeout(15, TimeUnit.SECONDS)
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .writeTimeout(15, TimeUnit.SECONDS)
                    .pingInterval(20, TimeUnit.SECONDS)
                    .build();
        }
        return wsHttpClient;
    }

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        try {
            PowerManager powerManager = (PowerManager) getSystemService(POWER_SERVICE);
            if (powerManager != null) {
                wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "SaphirSMS:WakeLock");
                wakeLock.acquire();
            }
        } catch (Exception ignored) {}
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForeground(NOTIF_ID, createNotification("🎱 Sentinelle active (Pub/Sub Temps Réel ⚡)"));

        // Vérification immédiate à l'initialisation ou sur demande
        executor.execute(() -> checkSupabaseAndSendSms());

        startSafetyPoll();

        // Connexion immédiate au flux Pub/Sub Supabase Realtime (écoute 24/7 en continu)
        initOrConnectRealtimeWebSocket();

        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {}
        }
        stopSafetyPoll();
        stopHeartbeat();
        if (reconnectRunnable != null) {
            handler.removeCallbacks(reconnectRunnable);
            reconnectRunnable = null;
        }
        if (realtimeWebSocket != null) {
            try {
                realtimeWebSocket.close(1000, "Service arrêté");
            } catch (Exception ignored) {}
            realtimeWebSocket = null;
        }
        if (wsHttpClient != null) {
            try {
                wsHttpClient.dispatcher().executorService().shutdown();
            } catch (Exception ignored) {}
            wsHttpClient = null;
        }
        executor.shutdown();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Service Sentinelle Saphir SMS",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("Surveille Supabase et transmet les résultats par SMS.");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    private Notification createNotification(String message) {
        Intent notifIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, notifIntent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("🎱 Saphir SMS Sentinel")
                .setContentText(message)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .build();
    }

    private void initOrConnectRealtimeWebSocket() {
        SharedPreferences prefs = getSharedPreferences("saphir_sms_prefs", Context.MODE_PRIVATE);
        String supabaseUrl = prefs.getString("supabase_url", "https://ueikhwdfmtnavqqscdoe.supabase.co").trim();
        if (supabaseUrl.isEmpty()) {
            supabaseUrl = "https://ueikhwdfmtnavqqscdoe.supabase.co";
        }
        String supabaseKey = prefs.getString("supabase_key", "").trim();
        if (supabaseKey.isEmpty()) {
            supabaseKey = MainActivity.getDefaultSupabaseKey();
        }

        if (supabaseUrl.isEmpty() || supabaseKey.isEmpty()) {
            return;
        }

        final String finalUrl = supabaseUrl;
        final String finalKey = supabaseKey;

        executor.execute(() -> {
            try {
                if (wsHttpClient == null) {
                    wsHttpClient = new OkHttpClient.Builder()
                            .readTimeout(0, TimeUnit.MILLISECONDS)
                            .connectTimeout(15, TimeUnit.SECONDS)
                            .pingInterval(20, TimeUnit.SECONDS)
                            .build();
                }

                if (realtimeWebSocket != null) {
                    try {
                        realtimeWebSocket.close(1000, "Reconnexion");
                    } catch (Exception ignored) {}
                    realtimeWebSocket = null;
                }

                String baseWs = finalUrl.replaceFirst("^http://", "ws://").replaceFirst("^https://", "wss://");
                if (!baseWs.endsWith("/")) {
                    baseWs += "/";
                }
                String wsUrl = baseWs + "realtime/v1/websocket?apikey=" + URLEncoder.encode(finalKey, "UTF-8") + "&vsn=1.0.0";

                Request request = new Request.Builder()
                        .url(wsUrl)
                        .addHeader("apikey", finalKey)
                        .addHeader("Authorization", "Bearer " + finalKey)
                        .build();

                broadcastLog("⚡ [Pub/Sub] Connexion au flux en direct Supabase Realtime...");

                realtimeWebSocket = wsHttpClient.newWebSocket(request, new WebSocketListener() {
                    @Override
                    public void onOpen(WebSocket webSocket, Response response) {
                        isWsConnected.set(true);
                        broadcastLog("⚡ [Pub/Sub] Connecté au serveur Realtime ! Inscription au canal 'saphir_sms'...");
                        sendJoinChannel(webSocket, finalKey);
                        startHeartbeat();
                        executor.execute(() -> checkSupabaseAndSendSms());
                    }

                    @Override
                    public void onMessage(WebSocket webSocket, String text) {
                        handleIncomingRealtimeMessage(text);
                    }

                    @Override
                    public void onClosed(WebSocket webSocket, int code, String reason) {
                        isWsConnected.set(false);
                        stopHeartbeat();
                        broadcastLog("⚠️ [Pub/Sub] Déconnecté (" + reason + "). Reconnexion programmée...");
                        scheduleReconnect();
                    }

                    @Override
                    public void onFailure(WebSocket webSocket, Throwable t, Response response) {
                        isWsConnected.set(false);
                        stopHeartbeat();
                        String err = (t != null && t.getMessage() != null) ? t.getMessage() : "Échec réseau";
                        broadcastLog("⚠️ [Pub/Sub] Interruption flux (" + err + "). Reconnexion dans 10s...");
                        scheduleReconnect();
                    }
                });
            } catch (Exception e) {
                isWsConnected.set(false);
                broadcastLog("❌ [Pub/Sub] Erreur WebSocket : " + e.getMessage());
                scheduleReconnect();
            }
        });
    }

    private void sendJoinChannel(WebSocket webSocket, String apiKey) {
        try {
            JSONObject payload = new JSONObject();
            JSONObject config = new JSONObject();
            JSONObject broadcast = new JSONObject();
            broadcast.put("self", true);
            config.put("broadcast", broadcast);
            payload.put("config", config);
            payload.put("access_token", apiKey);

            JSONObject msg = new JSONObject();
            msg.put("topic", TOPIC_REALTIME);
            msg.put("event", "phx_join");
            msg.put("payload", payload);
            msg.put("ref", "join_saphir");
            msg.put("join_ref", "join_saphir");

            webSocket.send(msg.toString());
        } catch (Exception e) {
            Log.e("SmsPollingService", "Erreur sendJoinChannel", e);
        }
    }

    private void startHeartbeat() {
        stopHeartbeat();
        heartbeatRunnable = new Runnable() {
            @Override
            public void run() {
                if (isWsConnected.get() && realtimeWebSocket != null) {
                    try {
                        JSONObject hb = new JSONObject();
                        hb.put("topic", "phoenix");
                        hb.put("event", "heartbeat");
                        hb.put("payload", new JSONObject());
                        hb.put("ref", "hb_" + System.currentTimeMillis());
                        realtimeWebSocket.send(hb.toString());
                    } catch (Exception ignored) {}
                    handler.postDelayed(this, HEARTBEAT_INTERVAL_MS);
                }
            }
        };
        handler.postDelayed(heartbeatRunnable, HEARTBEAT_INTERVAL_MS);
    }

    private void startSafetyPoll() {
        stopSafetyPoll();
        safetyPollRunnable = new Runnable() {
            @Override
            public void run() {
                executor.execute(() -> checkSupabaseAndSendSms());
                handler.postDelayed(this, SAFETY_POLL_INTERVAL_MS);
            }
        };
        handler.postDelayed(safetyPollRunnable, SAFETY_POLL_INTERVAL_MS);
    }

    private void stopSafetyPoll() {
        if (safetyPollRunnable != null) {
            handler.removeCallbacks(safetyPollRunnable);
            safetyPollRunnable = null;
        }
    }

    private void stopHeartbeat() {
        if (heartbeatRunnable != null) {
            handler.removeCallbacks(heartbeatRunnable);
            heartbeatRunnable = null;
        }
    }

    private void scheduleReconnect() {
        if (reconnectRunnable != null) {
            handler.removeCallbacks(reconnectRunnable);
        }
        reconnectRunnable = () -> {
            if (!isWsConnected.get()) {
                initOrConnectRealtimeWebSocket();
            }
        };
        handler.postDelayed(reconnectRunnable, RECONNECT_DELAY_MS);
    }

    private void handleIncomingRealtimeMessage(String text) {
        try {
            JSONObject json = new JSONObject(text);
            String topic = json.optString("topic", "");
            String event = json.optString("event", "");
            JSONObject payload = json.optJSONObject("payload");

            if ("phx_reply".equals(event)) {
                if (payload != null && "ok".equals(payload.optString("status"))) {
                    broadcastLog("✅ [Pub/Sub] Canal 'realtime:saphir_sms' ACTIF en direct ! Prêt à relayer.");
                }
                return;
            }

            if (TOPIC_REALTIME.equals(topic) || "broadcast".equals(event)) {
                String subEvent = "";
                if (payload != null) {
                    subEvent = payload.optString("event", "");
                }
                broadcastLog("⚡ [Pub/Sub] Signal reçu en direct (" + (!subEvent.isEmpty() ? subEvent : event) + ") ! Exécution immédiate...");
                executor.execute(() -> checkSupabaseAndSendSms());
                return;
            }

            if (text.contains("sms_trigger") || text.contains("CHECK_NOW") || text.contains("TEST_SMS")) {
                broadcastLog("⚡ [Pub/Sub] Notification détectée ! Exécution immédiate...");
                executor.execute(() -> checkSupabaseAndSendSms());
            }
        } catch (Exception e) {
            Log.e("SmsPollingService", "Erreur parse msg realtime", e);
        }
    }

    private void checkSupabaseAndSendSms() {
        SharedPreferences prefs = getSharedPreferences("saphir_sms_prefs", Context.MODE_PRIVATE);
        String supabaseUrl = prefs.getString("supabase_url", "https://ueikhwdfmtnavqqscdoe.supabase.co").trim();
        if (supabaseUrl.isEmpty()) {
            supabaseUrl = "https://ueikhwdfmtnavqqscdoe.supabase.co";
        }
        String supabaseKey = prefs.getString("supabase_key", "").trim();
        if (supabaseKey.isEmpty()) {
            supabaseKey = MainActivity.getDefaultSupabaseKey();
        }

        if (supabaseUrl.isEmpty() || supabaseKey.isEmpty()) {
            broadcastLog("⚠️ Clé ou URL Supabase manquante dans l'application ! Veuillez la configurer.");
            return;
        }

        String timeNow = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date());
        prefs.edit().putString("last_check_time", timeNow).apply();
        broadcastLog("[" + timeNow + "] 🔍 Vérification Supabase...");

        try {
            // 0. Traiter les commandes de test SMS en attente
            String cmdJsonStr = fetchFileFromSupabase(supabaseUrl, supabaseKey, "commandes_sms.json");
            if (cmdJsonStr != null && !cmdJsonStr.isEmpty()) {
                try {
                    JSONArray cmdArray = new JSONArray(cmdJsonStr);
                    boolean modifCmd = false;
                    int testsTrouves = 0;
                    for (int k = 0; k < cmdArray.length(); k++) {
                        JSONObject cmd = cmdArray.getJSONObject(k);
                        if ("en_attente".equals(cmd.optString("statut", ""))) {
                            testsTrouves++;
                            String telTest = cmd.optString("telephone", "");
                            String msgTest = cmd.optString("message", "");
                            if (!telTest.isEmpty() && !msgTest.isEmpty()) {
                                broadcastLog("🧪 Commande test trouvée pour " + telTest + "...");
                                if (ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
                                    broadcastLog("❌ ERREUR : Permission SEND_SMS non accordée sur ce téléphone ! Veuillez autoriser Saphir SMS dans Paramètres > Applications > Saphir SMS.");
                                    break;
                                }
                                try {
                                    SmsHelper.sendSafeSms(this, telTest, msgTest);
                                    cmd.put("statut", "envoye");
                                    cmd.put("date_envoi", new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date()));
                                    modifCmd = true;
                                    broadcastLog("✅ SMS de test envoyé avec succès à " + telTest + " !");
                                } catch (Exception eCmd) {
                                    cmd.put("statut", "erreur");
                                    cmd.put("erreur", eCmd.getMessage());
                                    modifCmd = true;
                                    broadcastLog("❌ Échec envoi test à " + telTest + " : " + eCmd.getMessage());
                                }
                            }
                        }
                    }
                    if (modifCmd) {
                        boolean okSave = saveFileToSupabase(supabaseUrl, supabaseKey, "commandes_sms.json", cmdArray.toString(4));
                        if (okSave) {
                            broadcastLog("💾 Commande mise à jour sur Supabase (statut=envoyé).");
                        } else {
                            broadcastLog("⚠️ Échec mise à jour statut sur Supabase.");
                        }
                    } else if (testsTrouves == 0) {
                        broadcastLog("ℹ️ Aucune commande de test en attente.");
                    }
                } catch (Exception eJson) {
                    broadcastLog("⚠️ Erreur format commandes_sms : " + eJson.getMessage());
                }
            } else {
                broadcastLog("ℹ️ Aucune commande SMS trouvée sur Supabase.");
            }

            // 0bis. Vérifier l'activation globale dans config_sms.json
            String cfgSmsStr = fetchFileFromSupabase(supabaseUrl, supabaseKey, "config_sms.json");
            if (cfgSmsStr != null && !cfgSmsStr.isEmpty()) {
                try {
                    JSONObject cfgObj = new JSONObject(cfgSmsStr);
                    boolean smsActif = cfgObj.optBoolean("sms_actif", true);
                    if (!smsActif) {
                        broadcastLog("⏸️ Service SMS désactivé globalement dans l'administration.");
                        return;
                    }
                } catch (Exception ignored) {}
            }

            // 1. Lire historique_matchs.json
            String matchsJsonStr = fetchFileFromSupabase(supabaseUrl, supabaseKey, "historique_matchs.json");
            if (matchsJsonStr == null || matchsJsonStr.isEmpty()) {
                broadcastLog("ℹ️ Aucun historique de match trouvé.");
                return;
            }

            JSONArray matchsArray = new JSONArray(matchsJsonStr);
            if (matchsArray.length() == 0) return;

            JSONObject dernierMatch = matchsArray.getJSONObject(matchsArray.length() - 1);
            String rec = dernierMatch.optString("equipe_receveur", dernierMatch.optString("receveur", ""));
            String vis = dernierMatch.optString("equipe_visiteur", dernierMatch.optString("visiteur", ""));
            String dateM = dernierMatch.optString("date", dernierMatch.optString("date_enregistrement", ""));
            String matchId = rec + "_" + vis + "_" + dateM;

            String dernierEnvoye = prefs.getString("dernier_match_envoye", "");
            if (matchId.equals(dernierEnvoye)) {
                broadcastLog("✅ Aucun nouveau match.");
                return;
            }

            broadcastLog("📢 NOUVEAU MATCH : " + rec + " vs " + vis + " (" + dateM + ")");

            // 2. Lire joueurs_sms.json
            String contactsJsonStr = fetchFileFromSupabase(supabaseUrl, supabaseKey, "joueurs_sms.json");
            JSONArray contactsArray = (contactsJsonStr != null && !contactsJsonStr.isEmpty()) ? new JSONArray(contactsJsonStr) : new JSONArray();

            String smsMessage = buildSmsMessage(dernierMatch);

            int sentCount = 0;

            for (int i = 0; i < contactsArray.length(); i++) {
                JSONObject c = contactsArray.getJSONObject(i);
                boolean consentement = c.optBoolean("consentement", false);
                String telephone = c.optString("telephone", "").replaceAll("[^0-9+]", "");
                String nom = c.optString("nom", "Joueur");

                if (consentement && telephone.length() >= 7) {
                    try {
                        SmsHelper.sendSafeSms(this, telephone, smsMessage);
                        broadcastLog("  -> SMS envoyé à " + nom + " (" + telephone + ")");
                        sentCount++;
                        Thread.sleep(1200); // Pause anti-flood
                    } catch (Exception eSms) {
                        broadcastLog("  ❌ Échec envoi à " + nom + " : " + eSms.getMessage());
                    }
                }
            }

            // 3. Mémoriser le match comme traité
            prefs.edit().putString("dernier_match_envoye", matchId).apply();
            broadcastLog("🎉 Succès : " + sentCount + " SMS expédié(s). Match mémorisé.");

        } catch (Exception e) {
            broadcastLog("❌ Erreur cycle vérification : " + e.getMessage());
        }
    }

    private String fetchFileFromSupabase(String baseUrl, String apiKey, String filename) {
        try {
            OkHttpClient client = getOkHttpClient();
            String url = baseUrl.replaceAll("/$", "") + "/rest/v1/saphir_files?filename=eq." + filename + "&select=content";
            Request request = new Request.Builder()
                    .url(url)
                    .addHeader("apikey", apiKey)
                    .addHeader("Authorization", "Bearer " + apiKey)
                    .addHeader("User-Agent", "SaphirSMS/1.1.0")
                    .build();

            try (Response response = client.newCall(request).execute()) {
                if (response.isSuccessful() && response.body() != null) {
                    String bodyStr = response.body().string();
                    JSONArray arr = new JSONArray(bodyStr);
                    if (arr.length() > 0) {
                        return arr.getJSONObject(0).optString("content", null);
                    }
                    return null;
                } else {
                    String err = response.body() != null ? response.body().string() : "";
                    broadcastLog("❌ Supabase " + filename + " HTTP " + response.code() + " : " + err);
                    return null;
                }
            }
        } catch (Exception e) {
            broadcastLog("❌ Erreur lecture Supabase (" + filename + ") : " + e.getMessage());
            return null;
        }
    }

    private boolean saveFileToSupabase(String baseUrl, String apiKey, String filename, String content) {
        try {
            OkHttpClient client = getOkHttpClient();
            String url = baseUrl.replaceAll("/$", "") + "/rest/v1/saphir_files";

            JSONObject body = new JSONObject();
            body.put("filename", filename);
            body.put("content", content);
            body.put("updated_at", new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).format(new Date()));

            MediaType mediaType = MediaType.parse("application/json; charset=utf-8");
            RequestBody reqBody = RequestBody.create(body.toString(), mediaType);

            Request request = new Request.Builder()
                    .url(url)
                    .addHeader("apikey", apiKey)
                    .addHeader("Authorization", "Bearer " + apiKey)
                    .addHeader("Content-Type", "application/json")
                    .addHeader("Prefer", "resolution=merge-duplicates")
                    .addHeader("User-Agent", "SaphirSMS/1.1.0")
                    .post(reqBody)
                    .build();

            try (Response response = client.newCall(request).execute()) {
                if (response.isSuccessful()) {
                    return true;
                } else {
                    String err = response.body() != null ? response.body().string() : "";
                    broadcastLog("❌ Supabase écriture " + filename + " HTTP " + response.code() + " : " + err);
                    return false;
                }
            }
        } catch (Exception e) {
            broadcastLog("❌ Erreur écriture Supabase (" + filename + ") : " + e.getMessage());
            return false;
        }
    }

    private String buildSmsMessage(JSONObject m) {
        String rec = m.optString("equipe_receveur", m.optString("receveur", "Receveur"));
        String vis = m.optString("equipe_visiteur", m.optString("visiteur", "Visiteur"));
        int totRec = m.optInt("total_points_receveur", m.optInt("points_receveur", 0));
        int totVis = m.optInt("total_points_visiteur", m.optInt("points_visiteur", 0));
        String dateStr = m.optString("date", m.optString("date_enregistrement", ""));

        StringBuilder sb = new StringBuilder();
        sb.append("[LIGUE SAPHIR] ").append(rec).append(" (").append(totRec).append(") vs ")
                .append(vis).append(" (").append(totVis).append(")\n")
                .append("Date : ").append(dateStr).append("\n\nPointages :\n");

        JSONObject totauxJ = m.optJSONObject("totaux_joueurs");
        if (totauxJ != null) {
            JSONArray keys = totauxJ.names();
            if (keys != null) {
                for (int i = 0; i < keys.length(); i++) {
                    String k = keys.optString(i);
                    sb.append("- ").append(k).append(" : ").append(totauxJ.optInt(k)).append("/24\n");
                }
            }
        }
        sb.append("\nClassement en direct sur l'app !");
        return sb.toString();
    }

    private void broadcastLog(String logMsg) {
        synchronized (RECENT_LOGS) {
            RECENT_LOGS.add(logMsg);
            if (RECENT_LOGS.size() > MAX_LOGS) {
                RECENT_LOGS.remove(0);
            }
        }
        Intent intent = new Intent("SAPHIR_SMS_LOG");
        intent.setPackage(getPackageName());
        intent.putExtra("log", logMsg);
        sendBroadcast(intent);
    }
}
