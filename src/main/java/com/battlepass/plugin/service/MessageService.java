package com.battlepass.plugin.service;

import com.battlepass.plugin.config.ConfigManager;
import com.battlepass.plugin.util.ColorUtil;
import com.battlepass.plugin.util.PlaceholderUtil;
import org.bukkit.command.CommandSender;
import org.bukkit.configuration.file.FileConfiguration;

import java.util.Collections;
import java.util.Map;

public final class MessageService {

    private final ConfigManager configManager;

    public MessageService(ConfigManager configManager) {
        this.configManager = configManager;
    }

    public void send(CommandSender sender, String key) {
        send(sender, key, Collections.emptyMap());
    }

    public void send(CommandSender sender, String key, Map<String, String> placeholders) {
        FileConfiguration messages = configManager.getMessages();
        String raw = messages.getString(key);
        if (raw == null || raw.isEmpty()) {
            return;
        }

        String prefix = messages.getString("prefix", "");
        String composed = PlaceholderUtil.apply(prefix + raw, placeholders);
        sender.sendMessage(ColorUtil.colorize(composed));
    }

    public String text(String key, Map<String, String> placeholders) {
        String raw = configManager.getMessages().getString(key, "");
        return ColorUtil.colorize(PlaceholderUtil.apply(raw, placeholders));
    }

    public String text(String key) {
        return text(key, Collections.emptyMap());
    }
}
