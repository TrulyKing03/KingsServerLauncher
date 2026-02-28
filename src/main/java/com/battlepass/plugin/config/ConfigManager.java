package com.battlepass.plugin.config;

import com.battlepass.plugin.BattlePassPlugin;
import org.bukkit.configuration.file.FileConfiguration;
import org.bukkit.configuration.file.YamlConfiguration;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public final class ConfigManager {

    private final BattlePassPlugin plugin;

    private File messagesFile;
    private File tiersFile;

    private FileConfiguration messages;
    private FileConfiguration tiers;

    public ConfigManager(BattlePassPlugin plugin) {
        this.plugin = plugin;
    }

    public void initialize() {
        plugin.saveDefaultConfig();
        createIfMissing("messages.yml");
        createTiersIfMissing();
        reload();
    }

    public void reload() {
        plugin.reloadConfig();

        messagesFile = new File(plugin.getDataFolder(), "messages.yml");
        tiersFile = new File(plugin.getDataFolder(), "tiers.yml");

        messages = YamlConfiguration.loadConfiguration(messagesFile);
        tiers = YamlConfiguration.loadConfiguration(tiersFile);
    }

    private void createIfMissing(String fileName) {
        File file = new File(plugin.getDataFolder(), fileName);
        if (!file.exists()) {
            plugin.saveResource(fileName, false);
        }
    }

    private void createTiersIfMissing() {
        File file = new File(plugin.getDataFolder(), "tiers.yml");
        if (file.exists()) {
            return;
        }

        YamlConfiguration generated = new YamlConfiguration();
        generated.set("settings.default-tier-material", "BOOK");
        generated.set("settings.default-tier-amount", 1);
        generated.set("settings.default-tier-glint", false);
        generated.set("settings.default-tier-flags", List.of("HIDE_ATTRIBUTES"));

        for (int tier = 1; tier <= 100; tier++) {
            String base = "tiers." + tier;
            long requiredXp = tier * 1000L;

            generated.set(base + ".required-xp", requiredXp);
            generated.set(base + ".item.material", "BOOK");
            generated.set(base + ".item.amount", 1);
            generated.set(base + ".item.custom-model-data", -1);
            generated.set(base + ".item.glint", tier % 10 == 0);
            generated.set(base + ".item.flags", List.of("HIDE_ATTRIBUTES"));
            generated.set(base + ".item.name", "&eTier " + tier);

            List<String> lore = new ArrayList<>();
            lore.add("&7Required XP: &f{required_xp}");
            lore.add("&7Free: &aLeft click to claim");
            lore.add("&7Premium: &6Right click to claim");
            generated.set(base + ".item.lore", lore);

            List<String> freeCommands = new ArrayList<>();
            freeCommands.add("give {player} experience_bottle " + Math.max(1, tier / 4));
            generated.set(base + ".free.rewards", freeCommands);
            generated.set(base + ".free.preview", List.of("&a+" + Math.max(1, tier / 4) + " XP Bottles"));

            List<String> premiumCommands = new ArrayList<>();
            premiumCommands.add("give {player} diamond " + Math.max(1, tier / 10));
            generated.set(base + ".premium.rewards", premiumCommands);
            generated.set(base + ".premium.preview", List.of("&6+" + Math.max(1, tier / 10) + " Diamonds"));
        }

        try {
            generated.save(file);
        } catch (IOException exception) {
            plugin.getLogger().warning("Failed to generate default tiers.yml: " + exception.getMessage());
        }
    }

    public FileConfiguration getMainConfig() {
        return plugin.getConfig();
    }

    public FileConfiguration getMessages() {
        return messages;
    }

    public FileConfiguration getTiers() {
        return tiers;
    }
}
