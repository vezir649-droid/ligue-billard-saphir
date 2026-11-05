package com.saphir.sms;

import android.content.Context;
import android.os.Build;
import android.telephony.SmsManager;
import java.util.ArrayList;
import java.util.List;

public class SmsHelper {

    public static SmsManager getSmsManager(Context context) {
        SmsManager sms = null;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            try {
                sms = context.getSystemService(SmsManager.class);
            } catch (Throwable ignored) {}
        }
        if (sms == null) {
            sms = SmsManager.getDefault();
        }
        return sms;
    }

    /**
     * Envoie un SMS de façon robuste sans jamais appeler SmsManager.divideMessage().
     * (SmsManager.divideMessage appelle en interne TelephonyManager.getGroupIdLevel1(),
     * ce qui déclenche une SecurityException sur Android 10+ pour les applications tierces).
     */
    public static void sendSafeSms(Context context, String destinationAddress, String text) throws Exception {
        if (destinationAddress == null || text == null || destinationAddress.trim().isEmpty()) {
            throw new IllegalArgumentException("Numéro ou message vide");
        }

        SmsManager sms = getSmsManager(context);
        if (sms == null) {
            throw new IllegalStateException("SmsManager indisponible sur cet appareil");
        }

        String phone = destinationAddress.replaceAll("[^0-9+]", "").trim();
        List<String> parts = splitMessageSafely(text);

        for (int i = 0; i < parts.size(); i++) {
            String part = parts.get(i);
            sms.sendTextMessage(phone, null, part, null, null);
            if (parts.size() > 1 && i < parts.size() - 1) {
                try {
                    Thread.sleep(600);
                } catch (InterruptedException ignored) {}
            }
        }
    }

    private static List<String> splitMessageSafely(String text) {
        List<String> parts = new ArrayList<>();
        if (text == null || text.isEmpty()) {
            return parts;
        }

        // Vérifier si le message contient des caractères Unicode non standard (GSM 7-bit)
        boolean isUnicode = false;
        for (int i = 0; i < text.length(); i++) {
            if (text.charAt(i) > 127) {
                isUnicode = true;
                break;
            }
        }

        int maxChunkSize = isUnicode ? 65 : 150;

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
