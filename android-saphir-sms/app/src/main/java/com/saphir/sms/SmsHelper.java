package com.saphir.sms;

import android.content.Context;
import android.os.Build;
import android.telephony.SmsManager;
import android.telephony.SubscriptionManager;
import java.util.ArrayList;
import java.util.List;

public class SmsHelper {

    public static SmsManager getSmsManager(Context context) {
        SmsManager sms = null;
        try {
            int subId = SubscriptionManager.getDefaultSmsSubscriptionId();
            if (subId != SubscriptionManager.INVALID_SUBSCRIPTION_ID) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    SmsManager sysSms = context.getSystemService(SmsManager.class);
                    if (sysSms != null) {
                        sms = sysSms.createForSubscriptionId(subId);
                    }
                }
                if (sms == null) {
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
     * Envoie un SMS de façon directe et non-bloquante sans jamais appeler SmsManager.divideMessage().
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
        if (phone.length() < 7) {
            throw new IllegalArgumentException("Numéro de téléphone invalide : " + destinationAddress);
        }

        String cleanText = cleanGsmText(text);
        ArrayList<String> parts = splitMessageSafely(cleanText);
        if (parts.isEmpty()) return;

        if (parts.size() == 1) {
            sms.sendTextMessage(phone, null, parts.get(0), null, null);
        } else {
            try {
                sms.sendMultipartTextMessage(phone, null, parts, null, null);
            } catch (Exception eMultipart) {
                for (int i = 0; i < parts.size(); i++) {
                    sms.sendTextMessage(phone, null, parts.get(i), null, null);
                    if (i < parts.size() - 1) {
                        try {
                            Thread.sleep(400);
                        } catch (InterruptedException ignored) {}
                    }
                }
            }
        }
    }

    public static String cleanGsmText(String text) {
        if (text == null) return "";
        String norm = java.text.Normalizer.normalize(text, java.text.Normalizer.Form.NFD)
                .replaceAll("\\p{M}", "");
        return norm.replace("’", "'").replace("œ", "oe").replace("Œ", "OE");
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
