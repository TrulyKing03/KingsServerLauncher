package com.battlepass.plugin.util;

import org.bukkit.ChatColor;

import java.util.ArrayList;
import java.util.List;

public final class ColorUtil {

    private ColorUtil() {
    }

    public static String colorize(String input) {
        if (input == null) {
            return "";
        }
        return ChatColor.translateAlternateColorCodes('&', input);
    }

    public static List<String> colorize(List<String> input) {
        List<String> output = new ArrayList<>();
        if (input == null) {
            return output;
        }
        for (String line : input) {
            output.add(colorize(line));
        }
        return output;
    }
}
