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

import androidx.core.app.NotificationCompat;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class SmsPollingService extends Service {
    private static final String CHANNEL_ID = "SaphirSmsChannel";
    private static final int NOTIF_ID = 101;
    private static final long INTERVAL_MS = 300000; // 5 minutes

    private final Handler handler = new Handler(Looper.getMainLooper());
    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private Runnable pollingRunnable;
    private PowerManager.WakeLock wakeLock;

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
        startForeground(NOTIF_ID, createNotification("🎱 Surveillance active (aux 5 min)"));

        if (intent != null && "ACTION_CHECK_NOW".equals(intent.getAction())) {
            executor.execute(() -> checkSupabaseAndSendSms());
            return START_STICKY;
        }

        if (pollingRunnable == null) {
            pollingRunnable = new Runnable() {
                @Override
                public void run() {
                    executor.execute(() -> checkSupabaseAndSendSms());
                    handler.postDelayed(this, INTERVAL_MS);
                }
            };
            handler.post(pollingRunnable);
        }

        return START_STICKY;
    }

    @Override
    public void onDestroy() {
        if (wakeLock != null && wakeLock.isHeld()) {
            try {
                wakeLock.release();
            } catch (Exception ignored) {}
        }
        if (pollingRunnable != null) {
            handler.removeCallbacks(pollingRunnable);
            pollingRunnable = null;
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
                                try {
                                    SmsHelper.sendSafeSms(this, telTest, msgTest);
                                    cmd.put("statut", "envoye");
                                    cmd.put("date_envoi", new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.getDefault()).format(new Date()));
                                    modifCmd = true;
                                    broadcastLog("✅ SMS de test envoyé avec succès à " + telTest + " !");
                                } catch (Exception eCmd) {
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
        HttpURLConnection conn = null;
        try {
            URL url = new URL(baseUrl.replaceAll("/$", "") + "/rest/v1/saphir_files?filename=eq." + filename + "&select=content");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("GET");
            conn.setRequestProperty("apikey", apiKey);
            conn.setRequestProperty("Authorization", "Bearer " + apiKey);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);

            if (conn.getResponseCode() == 200) {
                BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder sb = new StringBuilder();
                String line;
                while ((line = reader.readLine()) != null) sb.append(line);
                reader.close();

                JSONArray arr = new JSONArray(sb.toString());
                if (arr.length() > 0) {
                    return arr.getJSONObject(0).optString("content", null);
                }
            }
        } catch (Exception e) {
            Log.e("SmsPollingService", "Erreur fetch " + filename, e);
        } finally {
            if (conn != null) conn.disconnect();
        }
        return null;
    }

    private boolean saveFileToSupabase(String baseUrl, String apiKey, String filename, String content) {
        HttpURLConnection conn = null;
        try {
            URL url = new URL(baseUrl.replaceAll("/$", "") + "/rest/v1/saphir_files");
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("apikey", apiKey);
            conn.setRequestProperty("Authorization", "Bearer " + apiKey);
            conn.setRequestProperty("Content-Type", "application/json");
            conn.setRequestProperty("Prefer", "resolution=merge-duplicates");
            conn.setDoOutput(true);
            conn.setConnectTimeout(15000);
            conn.setReadTimeout(15000);

            JSONObject body = new JSONObject();
            body.put("filename", filename);
            body.put("content", content);
            body.put("updated_at", new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'", Locale.US).format(new Date()));

            OutputStream os = conn.getOutputStream();
            os.write(body.toString().getBytes(StandardCharsets.UTF_8));
            os.flush();
            os.close();

            int code = conn.getResponseCode();
            return code >= 200 && code < 300;
        } catch (Exception e) {
            Log.e("SmsPollingService", "Erreur save " + filename, e);
            return false;
        } finally {
            if (conn != null) conn.disconnect();
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
        Intent intent = new Intent("SAPHIR_SMS_LOG");
        intent.putExtra("log", logMsg);
        sendBroadcast(intent);
    }
}
