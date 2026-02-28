package com.battlepass.plugin.util;

import java.util.Map;

public final class PlaceholderUtil {

    private PlaceholderUtil() {
    }

    public static String apply(String input, Map<String, String> placeholders) {
        if (input == null || placeholders == null || placeholders.isEmpty()) {
            return input;
        }

        String result = input;
        for (Map.Entry<String, String> entry : placeholders.entrySet()) {
            String key = "{" + entry.getKey() + "}";
            result = result.replace(key, entry.getValue() == null ? "" : entry.getValue());
        }
        return result;
    }
}
