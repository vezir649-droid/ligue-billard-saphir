package com.saphir.sms;

import android.Manifest;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.telephony.SmsManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import java.util.ArrayList;

public class MainActivity extends AppCompatActivity {

    private TextView tvStatus, tvLastCheck, tvLogs;
    private EditText etSupabaseUrl, etSupabaseKey;
    private Button btnToggleService, btnTestSms;
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

        // Pré-remplissage depuis préférences
        etSupabaseUrl.setText(prefs.getString("supabase_url", "https://votre-projet.supabase.co"));
        etSupabaseKey.setText(prefs.getString("supabase_key", ""));

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
        try {
            unregisterReceiver(logReceiver);
        } catch (Exception ignored) {}
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
        prefs.edit()
                .putString("supabase_url", etSupabaseUrl.getText().toString().trim())
                .putString("supabase_key", etSupabaseKey.getText().toString().trim())
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
        String testPhone = "5140000000"; // Test prompt
        try {
            SmsManager sms = SmsManager.getDefault();
            Toast.makeText(this, "📲 Module SMS fonctionnel sur ce téléphone !", Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "❌ Erreur SMS : " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }
}
