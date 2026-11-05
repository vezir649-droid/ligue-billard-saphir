package com.saphir.sms;

import android.Manifest;
import android.app.AlertDialog;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.telephony.SmsManager;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.Locale;

public class MainActivity extends AppCompatActivity {

    private static final String DEFAULT_SUPABASE_URL = "https://ueikhwdfmtnavqqscdoe.supabase.co";

    private TextView tvStatus, tvLastCheck, tvLogs;
    private EditText etSupabaseUrl, etSupabaseKey;
    private Button btnToggleService, btnTestSms, btnSaveConfig;
    private SharedPreferences prefs;

    private final StringBuilder logBuilder = new StringBuilder();

    private final BroadcastReceiver logReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            String log = intent.getStringExtra("log");
            if (log != null) {
                logBuilder.append(log).append("\n");
                tvLogs.setText(logBuilder.toString());
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        prefs = getSharedPreferences("saphir_sms_prefs", MODE_PRIVATE);

        tvStatus = findViewById(R.id.tv_status);
        tvLastCheck = findViewById(R.id.tv_last_check);
        tvLogs = findViewById(R.id.tv_logs);
        etSupabaseUrl = findViewById(R.id.et_supabase_url);
        etSupabaseKey = findViewById(R.id.et_supabase_key);
        btnToggleService = findViewById(R.id.btn_toggle_service);
        btnTestSms = findViewById(R.id.btn_test_sms);
        btnSaveConfig = findViewById(R.id.btn_save_config);

        // Pré-remplissage avec l'URL officielle par défaut de la ligue
        String savedUrl = prefs.getString("supabase_url", DEFAULT_SUPABASE_URL);
        if (savedUrl.isEmpty()) {
            savedUrl = DEFAULT_SUPABASE_URL;
        }
        etSupabaseUrl.setText(savedUrl);
        etSupabaseKey.setText(prefs.getString("supabase_key", ""));

        // Sauvegarde automatique en direct dès que le texte est modifié ou collé
        TextWatcher autoSaveWatcher = new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int count, int after) {
                saveConfig();
            }
            @Override
            public void afterTextChanged(Editable s) {}
        };
        etSupabaseUrl.addTextChangedListener(autoSaveWatcher);
        etSupabaseKey.addTextChangedListener(autoSaveWatcher);

        // Bouton explicite pour rassurer l'utilisateur
        btnSaveConfig.setOnClickListener(v -> {
            saveConfig();
            Toast.makeText(this, "💾 Configuration Supabase enregistrée et conservée !", Toast.LENGTH_SHORT).show();
        });

        updateUiState(isServiceRunning());

        btnToggleService.setOnClickListener(v -> {
            checkAndRequestPermissions();
            boolean running = isServiceRunning();
            if (running) {
                stopSmsService();
            } else {
                saveConfig();
                startSmsService();
            }
        });

        btnTestSms.setOnClickListener(v -> {
            checkAndRequestPermissions();
            sendTestSms();
        });

        checkAndRequestPermissions();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(logReceiver, new IntentFilter("SAPHIR_SMS_LOG"), Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(logReceiver, new IntentFilter("SAPHIR_SMS_LOG"));
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        saveConfig();
        try {
            unregisterReceiver(logReceiver);
        } catch (Exception ignored) {}
    }

    @Override
    protected void onStop() {
        super.onStop();
        saveConfig();
    }

    private void checkAndRequestPermissions() {
        ArrayList<String> permissions = new ArrayList<>();
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(Manifest.permission.SEND_SMS);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.POST_NOTIFICATIONS);
            }
        }
        if (!permissions.isEmpty()) {
            ActivityCompat.requestPermissions(this, permissions.toArray(new String[0]), 123);
        }
    }

    private boolean isServiceRunning() {
        return prefs.getBoolean("is_running", false);
    }

    private void saveConfig() {
        String url = etSupabaseUrl.getText().toString().trim();
        String key = etSupabaseKey.getText().toString().trim();
        prefs.edit()
                .putString("supabase_url", url)
                .putString("supabase_key", key)
                .apply();
    }

    private void startSmsService() {
        Intent intent = new Intent(this, SmsPollingService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent);
        } else {
            startService(intent);
        }
        prefs.edit().putBoolean("is_running", true).apply();
        updateUiState(true);
        Toast.makeText(this, "🟢 Sentinelle SMS démarrée (aux 5 min)", Toast.LENGTH_SHORT).show();
    }

    private void stopSmsService() {
        Intent intent = new Intent(this, SmsPollingService.class);
        stopService(intent);
        prefs.edit().putBoolean("is_running", false).apply();
        updateUiState(false);
        Toast.makeText(this, "🔴 Sentinelle SMS arrêtée", Toast.LENGTH_SHORT).show();
    }

    private void updateUiState(boolean running) {
        if (running) {
            tvStatus.setText("🟢 Surveillance active (aux 5 min)");
            tvStatus.setTextColor(getResources().getColor(R.color.saphir_accent));
            btnToggleService.setText("ARRÊTER LA SURVEILLANCE");
            btnToggleService.setBackgroundColor(0xFFE53935); // Rouge
        } else {
            tvStatus.setText("🔴 Surveillance arrêtée");
            tvStatus.setTextColor(0xFFFF7777);
            btnToggleService.setText("DÉMARRER LA SURVEILLANCE");
            btnToggleService.setBackgroundColor(getResources().getColor(R.color.saphir_accent));
        }
    }

    private void sendTestSms() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.SEND_SMS}, 123);
            Toast.makeText(this, "Veuillez accorder l'autorisation d'envoi SMS.", Toast.LENGTH_SHORT).show();
            return;
        }

        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle("📲 Tester l'envoi d'un SMS");
        builder.setMessage("Entrez le numéro de cellulaire auquel envoyer le texto de test :");

        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_PHONE);
        input.setHint("ex: 5141234567 ou 4501234567");
        String savedPhone = prefs.getString("test_phone_number", "");
        if (!savedPhone.isEmpty()) {
            input.setText(savedPhone);
        }
        builder.setView(input);

        builder.setPositiveButton("ENVOYER", (dialog, which) -> {
            String phoneNumber = input.getText().toString().replaceAll("[^0-9+]", "").trim();
            if (phoneNumber.length() < 7) {
                Toast.makeText(this, "Numéro de téléphone invalide.", Toast.LENGTH_SHORT).show();
                return;
            }

            prefs.edit().putString("test_phone_number", phoneNumber).apply();

            String timeNow = new SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(new Date());
            String testMessage = "[SAPHIR SMS TEST] Connexion reussie a " + timeNow + " ! La Sentinelle de la Ligue de billard est active et prete.";

            try {
                SmsHelper.sendSafeSms(this, phoneNumber, testMessage);

                String logEntry = "[" + timeNow + "] ✅ SMS de test envoyé à " + phoneNumber;
                logBuilder.append(logEntry).append("\n");
                tvLogs.setText(logBuilder.toString());

                Toast.makeText(this, "✅ SMS de test envoyé à " + phoneNumber + " !", Toast.LENGTH_LONG).show();
            } catch (Exception e) {
                String errEntry = "[" + timeNow + "] ❌ Échec envoi test à " + phoneNumber + " : " + e.getMessage();
                logBuilder.append(errEntry).append("\n");
                tvLogs.setText(logBuilder.toString());
                Toast.makeText(this, "❌ Erreur SMS : " + e.getMessage(), Toast.LENGTH_LONG).show();
            }
        });

        builder.setNegativeButton("ANNULER", (dialog, which) -> dialog.cancel());
        builder.show();
    }
}
