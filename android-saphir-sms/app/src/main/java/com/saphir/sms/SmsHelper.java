package com.saphir.sms;

import android.app.Activity;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.os.Build;
import android.telephony.SmsManager;
import android.telephony.SubscriptionManager;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

public class SmsHelper {

    public static SmsManager getSmsManager(Context context) {
        SmsManager sms = null;
        try {
            int subId = SubscriptionManager.getDefaultSmsSubscriptionId();
            if (subId != SubscriptionManager.INVALID_SUBSCRIPTION_ID) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    sms = context.getSystemService(SmsManager.class).createForSubscriptionId(subId);
                } else {
                    sms = SmsManager.getSmsManagerForSubscriptionId(subId);
                }
            }
        } catch (Throwable ignored) {}

        if (sms == null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            try {
                sms = context.getSystemService(SmsManager.class);
            } catch (Throwable ignored) {}
        }

        if (sms == null) {
            try {
                sms = SmsManager.getDefault();
            } catch (Throwable ignored) {}
        }
        return sms;
    }

    /**
     * Envoie un SMS de façon robuste avec suivi du code de retour réseau du modem (PendingIntent).
     */
    public static void sendSafeSms(Context context, String destinationAddress, String text) throws Exception {
        if (destinationAddress == null || text == null || destinationAddress.trim().isEmpty()) {
            throw new IllegalArgumentException("Numéro ou message vide");
        }

        SmsManager sms = getSmsManager(context);
        if (sms == null) {
            throw new IllegalStateException("SmsManager indisponible sur cet appareil (aucun sous-système de téléphonie)");
        }

        String rawDigits = destinationAddress.replaceAll("[^0-9+]", "").trim();
        if (rawDigits.isEmpty()) {
            throw new IllegalArgumentException("Numéro de téléphone invalide : " + destinationAddress);
        }

        ArrayList<String> parts = splitMessageSafely(text);
        if (parts.isEmpty()) return;

        // Tenter d'abord avec le numéro saisi, puis avec préfixe +1 si échec (standard canadien)
        List<String> numberVariants = new ArrayList<>();
        numberVariants.add(rawDigits);
        if (rawDigits.length() == 10 && !rawDigits.startsWith("+") && !rawDigits.startsWith("1")) {
            numberVariants.add("+1" + rawDigits);
            numberVariants.add("1" + rawDigits);
        }

        Exception lastException = null;
        for (String targetPhone : numberVariants) {
            try {
                for (int i = 0; i < parts.size(); i++) {
                    sendSinglePartWithStatus(context, sms, targetPhone, parts.get(i));
                    if (i < parts.size() - 1) {
                        try {
                            Thread.sleep(600);
                        } catch (InterruptedException ignored) {}
                    }
                }
                return; // Envoi réussi pour toutes les parties !
            } catch (Exception e) {
                lastException = e;
            }
        }

        if (lastException != null) {
            throw lastException;
        }
    }

    private static void sendSinglePartWithStatus(Context context, SmsManager sms, String phone, String part) throws Exception {
        String actionSent = "SAPHIR_SMS_SENT_" + System.currentTimeMillis() + "_" + Math.round(Math.random() * 10000);
        Intent sentIntent = new Intent(actionSent);
        sentIntent.setPackage(context.getPackageName());

        int flags = PendingIntent.FLAG_ONE_SHOT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            flags |= PendingIntent.FLAG_MUTABLE;
        }
        PendingIntent sentPi = PendingIntent.getBroadcast(context, 0, sentIntent, flags);

        final AtomicInteger resCode = new AtomicInteger(-999);
        final CountDownLatch latch = new CountDownLatch(1);

        BroadcastReceiver receiver = new BroadcastReceiver() {
            @Override
            public void onReceive(Context c, Intent intent) {
                resCode.set(getResultCode());
                latch.countDown();
            }
        };

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            context.registerReceiver(receiver, new IntentFilter(actionSent), Context.RECEIVER_NOT_EXPORTED);
        } else {
            context.registerReceiver(receiver, new IntentFilter(actionSent));
        }

        try {
            sms.sendTextMessage(phone, null, part, sentPi, null);
            boolean done = latch.await(6, TimeUnit.SECONDS);

            if (!done) {
                // Réseau asynchrone sans confirmation immédiate, on accepte
                return;
            }

            int code = resCode.get();
            if (code == Activity.RESULT_OK) {
                return; // Succès confirmé par le modem et la tour cellulaire !
            }

            String explanation;
            switch (code) {
                case SmsManager.RESULT_ERROR_GENERIC_FAILURE:
                    explanation = "GENERIC_FAILURE (Modem/Opérateur a rejeté le SMS - Vérifiez si la carte SIM a un forfait actif ou si ce numéro est un cellulaire)";
                    break;
                case SmsManager.RESULT_ERROR_NO_SERVICE:
                    explanation = "NO_SERVICE (Aucun signal cellulaire - Téléphone hors réseau ou sans carte SIM active)";
                    break;
                case SmsManager.RESULT_ERROR_RADIO_OFF:
                    explanation = "RADIO_OFF (Mode avion actif ou réseau cellulaire éteint)";
                    break;
                case SmsManager.RESULT_ERROR_NULL_PDU:
                    explanation = "NULL_PDU (Format du message refusé par le modem)";
                    break;
                case SmsManager.RESULT_ERROR_LIMIT_EXCEEDED:
                    explanation = "LIMIT_EXCEEDED (Limite de SMS Android dépassée)";
                    break;
                default:
                    explanation = "Code erreur modem : " + code;
                    break;
            }
            throw new IOException("Erreur réseau cellulaire : " + explanation);

        } finally {
            try {
                context.unregisterReceiver(receiver);
            } catch (Exception ignored) {}
        }
    }

    private static ArrayList<String> splitMessageSafely(String text) {
        ArrayList<String> parts = new ArrayList<>();
        if (text == null || text.isEmpty()) {
            return parts;
        }

        boolean isUnicode = false;
        for (int i = 0; i < text.length(); i++) {
            if (text.charAt(i) > 127) {
                isUnicode = true;
                break;
            }
        }

        int maxChunkSize = isUnicode ? 67 : 153;

        if (text.length() <= maxChunkSize) {
            parts.add(text);
            return parts;
        }

        int start = 0;
        int totalLen = text.length();
        while (start < totalLen) {
            int end = Math.min(start + maxChunkSize, totalLen);
            if (end < totalLen && Character.isHighSurrogate(text.charAt(end - 1))) {
                end--;
            }
            parts.add(text.substring(start, end));
            start = end;
        }

        return parts;
    }
}
